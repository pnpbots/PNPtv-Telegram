# -*- coding: utf-8 -*-
"""
GESTOR DE SUSCRIPCIONES MEJORADO Y UNIFICADO
==========================================
Sistema completo de gestión automática de canales con mejoras de rendimiento y seguridad
"""

import asyncio
import backoff
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union
import logging
import hashlib
import hmac

try:
    import asyncpg
except ImportError as exc:
    raise ImportError(
        "asyncpg is required. Install dependencies using 'pip install -r requirements.txt'"
    ) from exc

from bot.config import (
    CHANNELS, PLANS, BOT_TOKEN, DATABASE_URL, ADMIN_IDS, 
    get_plan_channels, get_plan_channel_names, REMINDER_DAYS_BEFORE_EXPIRY,
    DATABASE_CONFIG, RATE_LIMIT_CONFIG, SECURITY_CONFIG
)
import sys
from telegram import Bot
from telegram.error import TelegramError, RetryAfter

logger = logging.getLogger(__name__)

class EnhancedSubscriberManager:
    """Gestor unificado de suscripciones con gestión automática de canales y mejoras de seguridad"""
    
    def __init__(self, db_url: str = DATABASE_URL):
        if not db_url:
            raise ValueError("DATABASE_URL must be provided")
        self.db_url = db_url
        self.pool = None
        self.bot = Bot(token=BOT_TOKEN)
        self._metrics = {
            'invites_sent': 0,
            'invites_failed': 0,
            'payments_processed': 0,
            'reminders_sent': 0
        }
        
    async def initialize(self):
        """Inicializar pool de conexiones optimizado y tablas"""
        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.db_url,
                min_size=DATABASE_CONFIG["min_size"],
                max_size=DATABASE_CONFIG["max_size"],
                command_timeout=DATABASE_CONFIG["command_timeout"]
            )
            await self._ensure_tables()
            logger.info("✅ Enhanced SubscriberManager initialized with optimized pool")
        except Exception as exc:
            logger.error(f"❌ Database connection failed: {exc}")
            raise ConnectionError(
                "Could not connect to the database. Check DATABASE_URL and that the server is running."
            ) from exc

    async def _ensure_tables(self) -> None:
        """Crear tablas con mejoras de índices y estructura optimizada"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
            
        async with self.pool.acquire() as conn:
            # Tabla de suscriptores con mejoras
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id BIGINT PRIMARY KEY,
                    plan TEXT NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    transaction_id TEXT UNIQUE,
                    auto_renewed BOOLEAN DEFAULT FALSE,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    payment_amount DECIMAL(10,2),
                    payment_currency TEXT DEFAULT 'USD',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            
            # Tabla de usuarios mejorada
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'en',
                    age_verified BOOLEAN DEFAULT FALSE,
                    terms_accepted BOOLEAN DEFAULT FALSE,
                    terms_accepted_at TIMESTAMP NULL,
                    last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
                    is_blocked BOOLEAN DEFAULT FALSE,
                    registration_ip TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            
            # Tabla de acceso a canales mejorada
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_access (
                    user_id BIGINT,
                    channel_id BIGINT,
                    channel_name TEXT,
                    granted_at TIMESTAMP DEFAULT NOW(),
                    revoked_at TIMESTAMP NULL,
                    invite_link TEXT,
                    access_count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, channel_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """
            )
            
            # Tabla de logs de actividad mejorada
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action TEXT NOT NULL,
                    details JSONB,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
                """
            )
            
            # Tabla de métricas (nueva)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    metric_value INTEGER NOT NULL,
                    metric_date DATE DEFAULT CURRENT_DATE,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(metric_name, metric_date)
                )
                """
            )
            
            # Crear índices optimizados
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_subscribers_expires_at ON subscribers (expires_at)",
                "CREATE INDEX IF NOT EXISTS idx_subscribers_reminder ON subscribers (expires_at, reminder_sent) WHERE reminder_sent = FALSE",
                "CREATE INDEX IF NOT EXISTS idx_subscribers_transaction ON subscribers (transaction_id) WHERE transaction_id IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_users_language ON users (language)",
                "CREATE INDEX IF NOT EXISTS idx_users_age_verified ON users (age_verified) WHERE age_verified = TRUE",
                "CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users (last_seen)",
                "CREATE INDEX IF NOT EXISTS idx_channel_access_user ON channel_access (user_id)",
                "CREATE INDEX IF NOT EXISTS idx_channel_access_active ON channel_access (user_id, channel_id) WHERE revoked_at IS NULL",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_action ON activity_logs (user_id, action)",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs (timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_name_date ON metrics (metric_name, metric_date)"
            ]
            
            for index_sql in indexes:
                await conn.execute(index_sql)
            
            logger.info("✅ Database schema and indexes created/updated")

    @backoff.on_exception(
        backoff.expo,
        (TelegramError, RetryAfter),
        max_tries=RATE_LIMIT_CONFIG["max_retries"],
        base=2
    )
    async def _send_with_retry(self, method, *args, **kwargs):
        """Enviar mensaje con reintentos automáticos"""
        return await method(*args, **kwargs)

    async def add_subscriber(self, user_id: int, plan_name: str, transaction_id: str = None, 
                           payment_amount: float = None, payment_currency: str = "USD") -> bool:
        """Agregar suscriptor con validaciones mejoradas y métricas"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
            
        try:
            # Buscar información del plan
            plan_info = None
            for key, info in PLANS.items():
                if info["name"] == plan_name:
                    plan_info = info
                    break
            
            if not plan_info:
                logger.error(f"❌ Plan {plan_name} not found")
                await self._log_activity(user_id, "subscription_failed", {"reason": "plan_not_found", "plan": plan_name})
                return False

            # Validar datos
            if payment_amount is None:
                payment_amount = float(plan_info["price"].replace("$", ""))

            duration_days = plan_info["duration_days"]
            start_date = datetime.now(timezone.utc)
            expiry_date = start_date + timedelta(days=duration_days)

            async with self.pool.acquire() as conn:
                # Verificar si ya existe suscripción activa
                existing = await conn.fetchrow(
                    "SELECT expires_at FROM subscribers WHERE user_id = $1", user_id
                )
                
                if existing and existing['expires_at'] > start_date:
                    logger.warning(f"⚠️ User {user_id} already has active subscription")
                    # Extender suscripción existente en lugar de reemplazar
                    new_expiry = existing['expires_at'] + timedelta(days=duration_days)
                    await conn.execute(
                        """
                        UPDATE subscribers SET 
                            expires_at = $1, 
                            reminder_sent = FALSE,
                            updated_at = NOW()
                        WHERE user_id = $2
                        """,
                        new_expiry, user_id
                    )
                    expiry_date = new_expiry
                else:
                    # Insertar nueva suscripción
                    await conn.execute(
                        """
                        INSERT INTO subscribers (user_id, plan, start_date, expires_at, transaction_id, 
                                               payment_amount, payment_currency, reminder_sent)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE)
                        ON CONFLICT (user_id) DO UPDATE SET
                            plan=EXCLUDED.plan,
                            start_date=EXCLUDED.start_date,
                            expires_at=EXCLUDED.expires_at,
                            transaction_id=EXCLUDED.transaction_id,
                            payment_amount=EXCLUDED.payment_amount,
                            payment_currency=EXCLUDED.payment_currency,
                            reminder_sent=FALSE,
                            updated_at=NOW()
                        """,
                        user_id, plan_name, start_date, expiry_date, transaction_id,
                        payment_amount, payment_currency
                    )
                
                # Log de actividad con detalles completos
                await self._log_activity(user_id, "subscription_created", {
                    "plan": plan_name,
                    "expires": expiry_date.isoformat(),
                    "transaction_id": transaction_id,
                    "amount": payment_amount,
                    "currency": payment_currency
                })

            # Otorgar acceso a canales específicos del plan
            await self._grant_channel_access(user_id, plan_name)
            
            # Recordar usuario
            await self.record_user(user_id)
            
            # Actualizar métricas
            self._metrics['payments_processed'] += 1
            await self._update_metric("payments_processed", 1)
            
            logger.info(f"✅ Subscriber {user_id} added successfully with plan {plan_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding subscriber: {e}")
            await self._log_activity(user_id, "subscription_error", {"error": str(e)})
            return False

    async def _grant_channel_access(self, user_id: int, plan_name: str = None) -> None:
        """Otorgar acceso a canales con rate limiting mejorado"""
        success_channels = []
        failed_channels = []
        
        # Obtener canales específicos del plan
        if plan_name:
            channel_ids = get_plan_channels(plan_name)
            channel_names = get_plan_channel_names(plan_name)
        else:
            channel_ids = list(CHANNELS.values())
            channel_names = list(CHANNELS.keys())
        
        for i, channel_id in enumerate(channel_ids):
            channel_name = channel_names[i] if i < len(channel_names) else f"channel_{i+1}"
            
            try:
                # Generar enlace de invitación con retry
                invite_link = await self._send_with_retry(
                    self.bot.create_chat_invite_link,
                    chat_id=channel_id,
                    member_limit=1,
                    expire_date=int((datetime.now() + timedelta(days=1)).timestamp())
                )
                
                # Enviar enlace al usuario con retry
                await self._send_with_retry(
                    self.bot.send_message,
                    chat_id=user_id,
                    text=f"🎬 **Welcome to {channel_name}!**\n\n"
                         f"Click here to join: {invite_link.invite_link}\n\n"
                         f"⏰ Link expires in 24 hours",
                    parse_mode='Markdown'
                )
                
                # Registrar acceso en la base de datos
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO channel_access (user_id, channel_id, channel_name, granted_at, invite_link)
                        VALUES ($1, $2, $3, NOW(), $4)
                        ON CONFLICT (user_id, channel_id) DO UPDATE SET
                            granted_at = NOW(),
                            revoked_at = NULL,
                            channel_name = EXCLUDED.channel_name,
                            invite_link = EXCLUDED.invite_link,
                            access_count = channel_access.access_count + 1
                        """,
                        user_id, channel_id, channel_name, invite_link.invite_link
                    )
                
                success_channels.append(channel_name)
                self._metrics['invites_sent'] += 1
                logger.info(f"✅ Access granted to {user_id} for channel {channel_name}")
                
            except TelegramError as e:
                failed_channels.append(channel_name)
                self._metrics['invites_failed'] += 1
                logger.error(f"❌ Error granting access to {user_id} for channel {channel_name}: {e}")
            
            # Rate limiting optimizado
            await asyncio.sleep(RATE_LIMIT_CONFIG["invite_delay"])
        
        # Mensaje de resumen mejorado
        if success_channels:
            summary_text = f"✅ **Access Granted Successfully!**\n\n"
            summary_text += f"📺 Channels available: {len(success_channels)}\n"
            summary_text += f"🎬 Start enjoying exclusive content now!"
            
            if failed_channels:
                summary_text += f"\n\n⚠️ Some channels had issues: {', '.join(failed_channels)}\n"
                summary_text += f"Contact support: support@pnptv.app"
            
            await self._send_with_retry(
                self.bot.send_message,
                chat_id=user_id,
                text=summary_text,
                parse_mode='Markdown'
            )
        
        # Actualizar métricas
        await self._update_metric("invites_sent", len(success_channels))
        if failed_channels:
            await self._update_metric("invites_failed", len(failed_channels))

    async def revoke_channel_access(self, user_id: int) -> None:
        """Revocar acceso a canales con logging mejorado"""
        revoked_channels = []
        
        # Obtener canales a los que el usuario tiene acceso
        async with self.pool.acquire() as conn:
            channel_rows = await conn.fetch(
                """
                SELECT channel_id, channel_name FROM channel_access 
                WHERE user_id = $1 AND revoked_at IS NULL
                """,
                user_id
            )
        
        for row in channel_rows:
            channel_id = row['channel_id']
            channel_name = row['channel_name']
            
            try:
                # Intentar expulsar al usuario del canal con retry
                await self._send_with_retry(
                    self.bot.ban_chat_member,
                    chat_id=channel_id,
                    user_id=user_id
                )
                
                # Inmediatamente desbanearlo
                await self._send_with_retry(
                    self.bot.unban_chat_member,
                    chat_id=channel_id,
                    user_id=user_id
                )
                
                revoked_channels.append(channel_name)
                logger.info(f"✅ Access revoked for {user_id} from channel {channel_name}")
                
            except TelegramError as e:
                logger.error(f"❌ Error revoking access for {user_id} from channel {channel_name}: {e}")
        
        # Actualizar base de datos
        if revoked_channels:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE channel_access 
                    SET revoked_at = NOW() 
                    WHERE user_id = $1 AND revoked_at IS NULL
                    """,
                    user_id
                )
            
            await self._log_activity(user_id, "access_revoked", {
                "channels": revoked_channels,
                "reason": "subscription_expired"
            })
            
            # Notificar al usuario con retry
            try:
                await self._send_with_retry(
                    self.bot.send_message,
                    chat_id=user_id,
                    text="⚠️ **Subscription Expired**\n\n"
                         "Your access to premium channels has been revoked.\n"
                         "Renew your subscription to regain access!\n\n"
                         "Use /plans to see available options.",
                    parse_mode='Markdown'
                )
            except TelegramError as e:
                logger.warning(f"⚠️ Could not notify user {user_id} about revocation: {e}")

    async def check_expired_subscriptions(self) -> List[int]:
        """Verificar y procesar suscripciones expiradas con mejoras"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        expired_users = []
        
        try:
            async with self.pool.acquire() as conn:
                # Query optimizada para encontrar suscripciones expiradas
                rows = await conn.fetch(
                    """
                    SELECT s.user_id, s.plan, s.expires_at 
                    FROM subscribers s
                    WHERE s.expires_at <= NOW() 
                    AND NOT EXISTS (
                        SELECT 1 FROM activity_logs al 
                        WHERE al.user_id = s.user_id 
                        AND al.action = 'access_revoked' 
                        AND al.timestamp > s.expires_at
                    )
                    ORDER BY s.expires_at
                    """
                )
                
                for row in rows:
                    user_id = row['user_id']
                    plan = row['plan']
                    expired_users.append(user_id)
                    
                    # Revocar acceso
                    await self.revoke_channel_access(