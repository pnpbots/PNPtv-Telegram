# -*- coding: utf-8 -*-
"""
SISTEMA DE BROADCAST MEJORADO CON RATE LIMITING Y MÉTRICAS
=========================================================
Gestión de mensajes masivos con optimizaciones de rendimiento y seguridad
"""

from __future__ import annotations

import asyncio
import backoff
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import logging

from telegram import Bot
from telegram.error import TelegramError, RetryAfter

from bot.enhanced_subscriber_manager import get_subscriber_manager  # ✅ CORREGIDO: Import correcto
from bot.config import BOT_TOKEN, RATE_LIMIT_CONFIG, SECURITY_CONFIG

logger = logging.getLogger(__name__)

class BroadcastManager:
    """Gestor de broadcasts con programación, segmentación y rate limiting mejorado"""

    def __init__(self, bot: Bot | None = None):
        self.bot = bot or Bot(token=BOT_TOKEN)
        self.scheduled: List[tuple[datetime, asyncio.Task]] = []
        self.metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'users_reached': 0,
            'broadcasts_today': 0,
            'last_broadcast': None
        }
        self._daily_broadcast_count = 0
        self._last_reset_date = datetime.now(timezone.utc).date()

    def _check_daily_limit(self) -> bool:
        """Verificar límite diario de broadcasts"""
        current_date = datetime.now(timezone.utc).date()
        
        # Reset contador si es un nuevo día
        if current_date != self._last_reset_date:
            self._daily_broadcast_count = 0
            self._last_reset_date = current_date
        
        return self._daily_broadcast_count < SECURITY_CONFIG["max_broadcast_per_day"]

    @backoff.on_exception(
        backoff.expo,
        (TelegramError, RetryAfter),
        max_tries=RATE_LIMIT_CONFIG["max_retries"],
        base=2
    )
    async def _send_message_with_retry(self, chat_id: int, **kwargs) -> bool:
        """Enviar mensaje individual con reintentos automáticos"""
        try:
            if kwargs.get('photo'):
                await self.bot.send_photo(chat_id=chat_id, **kwargs)
            elif kwargs.get('video'):
                await self.bot.send_video(chat_id=chat_id, **kwargs)
            elif kwargs.get('animation'):
                await self.bot.send_animation(chat_id=chat_id, **kwargs)
            elif kwargs.get('text'):
                await self.bot.send_message(chat_id=chat_id, **kwargs)
            else:
                logger.warning(f"No valid content to send to {chat_id}")
                return False
            
            return True
            
        except TelegramError as e:
            # Log específico para diferentes tipos de errores
            if "blocked" in str(e).lower():
                logger.info(f"User {chat_id} has blocked the bot")
                # Marcar usuario como bloqueado en la base de datos
                try:
                    manager = await get_subscriber_manager()
                    await manager.record_user(chat_id, is_blocked=True)
                except Exception as db_error:
                    logger.warning(f"Failed to mark user {chat_id} as blocked: {db_error}")
            elif "not found" in str(e).lower():
                logger.info(f"User {chat_id} not found or deleted account")
            else:
                logger.error(f"Error sending message to {chat_id}: {e}")
            
            return False

    async def send(
        self,
        text: Optional[str] = None,
        parse_mode: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        animation: Optional[str] = None,
        language: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Enviar broadcast con métricas detalladas y manejo de errores mejorado
        
        Args:
            text: Texto del mensaje
            parse_mode: Modo de formato (Markdown, HTML)
            photo: URL o file_id de la foto
            video: URL o file_id del video
            animation: URL o file_id del GIF
            language: Filtro de idioma ('en', 'es', None para todos)
            statuses: Filtro de estados (['active'], ['churned'], etc.)
            dry_run: Solo contar usuarios sin enviar mensajes
            
        Returns:
            Dict con métricas del broadcast
        """
        
        # Verificar límite diario
        if not dry_run and not self._check_daily_limit():
            raise ValueError(f"Daily broadcast limit reached ({SECURITY_CONFIG['max_broadcast_per_day']})")
        
        # Validar contenido
        if not any([text, photo, video, animation]):
            raise ValueError("At least one content type must be provided")
        
        broadcast_start = datetime.now(timezone.utc)
        
        # Obtener usuarios filtrados
        try:
            manager = await get_subscriber_manager()
            users = await manager.get_users(language=language, statuses=statuses)
        except Exception as e:
            logger.error(f"Error fetching users for broadcast: {e}")
            raise
        
        if dry_run:
            return {
                'dry_run': True,
                'target_users': len(users),
                'filters': {
                    'language': language,
                    'statuses': statuses
                },
                'estimated_duration': len(users) * RATE_LIMIT_CONFIG["broadcast_delay"]
            }
        
        logger.info(f"Starting broadcast to {len(users)} users with filters: language={language}, statuses={statuses}")
        
        # Preparar argumentos del mensaje
        message_kwargs = {
            'text': text,
            'parse_mode': parse_mode,
            'photo': photo,
            'video': video,
            'animation': animation
        }
        
        # Remover argumentos vacíos
        message_kwargs = {k: v for k, v in message_kwargs.items() if v is not None}
        
        # Contadores para métricas
        sent_count = 0
        failed_count = 0
        blocked_users = []
        
        # Enviar mensajes con rate limiting
        for i, user in enumerate(users):
            user_id = user["user_id"]
            
            try:
                success = await self._send_message_with_retry(user_id, **message_kwargs)
                
                if success:
                    sent_count += 1
                    self.metrics['messages_sent'] += 1
                else:
                    failed_count += 1
                    self.metrics['messages_failed'] += 1
                    blocked_users.append(user_id)
                
                # Rate limiting mejorado
                if i < len(users) - 1:  # No hacer delay en el último mensaje
                    await asyncio.sleep(RATE_LIMIT_CONFIG["broadcast_delay"])
                
                # Log de progreso cada 100 mensajes
                if (i + 1) % 100 == 0:
                    logger.info(f"Broadcast progress: {i + 1}/{len(users)} messages processed")
                    
            except Exception as e:
                logger.error(f"Unexpected error sending to user {user_id}: {e}")
                failed_count += 1
                self.metrics['messages_failed'] += 1
        
        # Actualizar métricas
        broadcast_end = datetime.now(timezone.utc)
        duration = (broadcast_end - broadcast_start).total_seconds()
        
        self._daily_broadcast_count += 1
        self.metrics['users_reached'] = sent_count
        self.metrics['broadcasts_today'] = self._daily_broadcast_count
        self.metrics['last_broadcast'] = broadcast_end
        
        # Resultado del broadcast
        result = {
            'broadcast_id': f"BC_{int(broadcast_start.timestamp())}",
            'started_at': broadcast_start.isoformat(),
            'completed_at': broadcast_end.isoformat(),
            'duration_seconds': duration,
            'target_users': len(users),
            'messages_sent': sent_count,
            'messages_failed': failed_count,
            'success_rate': (sent_count / len(users) * 100) if users else 0,
            'blocked_users': len(blocked_users),
            'filters_applied': {
                'language': language,
                'statuses': statuses
            },
            'content_type': self._get_content_type(message_kwargs),
            'rate_limit_delay': RATE_LIMIT_CONFIG["broadcast_delay"]
        }
        
        logger.info(
            f"Broadcast completed: {sent_count}/{len(users)} sent "
            f"({result['success_rate']:.1f}% success rate) in {duration:.1f}s"
        )
        
        return result

    def schedule(
        self,
        when: datetime,
        *,
        text: Optional[str] = None,
        parse_mode: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        animation: Optional[str] = None,
        language: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> str:
        """
        Programar broadcast con validaciones mejoradas
        
        Returns:
            str: ID único del broadcast programado
        """
        now = datetime.now(timezone.utc)
        
        # Validaciones de tiempo
        if when < now:
            raise ValueError("Scheduled time must be in the future")
        
        if when > now + timedelta(hours=72):
            raise ValueError("Cannot schedule broadcasts more than 72 hours in advance")
        
        # Verificar límite de broadcasts programados para el día
        target_date = when.date()
        scheduled_for_day = sum(
            1 for (scheduled_time, _) in self.scheduled 
            if scheduled_time.date() == target_date
        )
        
        if scheduled_for_day >= SECURITY_CONFIG["max_broadcast_per_day"]:
            raise ValueError(f"Maximum {SECURITY_CONFIG['max_broadcast_per_day']} broadcasts per day limit reached for {target_date}")
        
        # Validar contenido
        if not any([text, photo, video, animation]):
            raise ValueError("At least one content type must be provided")
        
        # Crear ID único para el broadcast
        broadcast_id = f"SCHED_{int(when.timestamp())}_{len(self.scheduled)}"
        
        async def _scheduled_task():
            """Tarea programada para ejecutar el broadcast"""
            try:
                # Calcular delay hasta el momento programado
                delay = (when - datetime.now(timezone.utc)).total_seconds()
                if delay > 0:
                    logger.info(f"Waiting {delay:.1f}s for scheduled broadcast {broadcast_id}")
                    await asyncio.sleep(delay)
                
                # Ejecutar el broadcast
                logger.info(f"Executing scheduled broadcast {broadcast_id}")
                result = await self.send(
                    text=text,
                    parse_mode=parse_mode,
                    photo=photo,
                    video=video,
                    animation=animation,
                    language=language,
                    statuses=statuses,
                )
                
                logger.info(f"Scheduled broadcast {broadcast_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error executing scheduled broadcast {broadcast_id}: {e}")
            finally:
                # Auto-limpiar de la lista
                self.scheduled = [
                    (t, task) for (t, task) in self.scheduled 
                    if task != asyncio.current_task()
                ]

        # Crear y programar la tarea
        task = asyncio.create_task(_scheduled_task())
        self.scheduled.append((when, task))
        
        # Callback para limpieza cuando termine
        def _cleanup_callback(fut: asyncio.Task) -> None:
            """Limpiar tareas completadas"""
            self.scheduled = [
                (w, t) for (w, t) in self.scheduled if t is not fut
            ]

        task.add_done_callback(_cleanup_callback)
        
        logger.info(f"Broadcast scheduled for {when.isoformat()} with ID {broadcast_id}")
        return broadcast_id

    def get_scheduled_broadcasts(self) -> List[Dict[str, Any]]:
        """Obtener lista de broadcasts programados"""
        scheduled_list = []
        
        for scheduled_time, task in self.scheduled:
            if not task.done():
                scheduled_list.append({
                    'scheduled_time': scheduled_time.isoformat(),
                    'time_remaining': (scheduled_time - datetime.now(timezone.utc)).total_seconds(),
                    'task_status': 'pending',
                    'can_cancel': True
                })
        
        return sorted(scheduled_list, key=lambda x: x['scheduled_time'])

    def cancel_scheduled_broadcast(self, broadcast_time: datetime) -> bool:
        """Cancelar broadcast programado"""
        for i, (scheduled_time, task) in enumerate(self.scheduled):
            if scheduled_time == broadcast_time and not task.done():
                task.cancel()
                self.scheduled.pop(i)
                logger.info(f"Cancelled scheduled broadcast for {broadcast_time.isoformat()}")
                return True
        
        return False

    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas del sistema de broadcast"""
        return {
            **self.metrics,
            'scheduled_count': len([t for _, t in self.scheduled if not t.done()]),
            'daily_broadcasts_used': self._daily_broadcast_count,
            'daily_broadcasts_remaining': SECURITY_CONFIG["max_broadcast_per_day"] - self._daily_broadcast_count,
            'rate_limit_delay': RATE_LIMIT_CONFIG["broadcast_delay"]
        }

    def _get_content_type(self, message_kwargs: Dict[str, Any]) -> str:
        """Determinar tipo de contenido del mensaje"""
        if message_kwargs.get('photo'):
            return 'photo'
        elif message_kwargs.get('video'):
            return 'video'
        elif message_kwargs.get('animation'):
            return 'animation'
        elif message_kwargs.get('text'):
            return 'text'
        else:
            return 'unknown'

    async def test_broadcast(self, admin_user_id: int, **kwargs) -> Dict[str, Any]:
        """Enviar broadcast de prueba solo al administrador"""
        logger.info(f"Sending test broadcast to admin {admin_user_id}")
        
        try:
            success = await self._send_message_with_retry(admin_user_id, **kwargs)
            
            return {
                'test_completed': True,
                'success': success,
                'admin_user_id': admin_user_id,
                'content_type': self._get_content_type(kwargs),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in test broadcast: {e}")
            return {
                'test_completed': False,
                'success': False,
                'error': str(e),
                'admin_user_id': admin_user_id
            }

    async def cleanup_old_scheduled(self) -> int:
        """Limpiar broadcasts programados completados o cancelados"""
        initial_count = len(self.scheduled)
        
        self.scheduled = [
            (time, task) for time, task in self.scheduled 
            if not task.done()
        ]
        
        cleaned_count = initial_count - len(self.scheduled)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old scheduled broadcasts")
        
        return cleaned_count

# Instancia global singleton
_broadcast_manager_instance = None

def get_broadcast_manager() -> BroadcastManager:
    """Obtener instancia global del broadcast manager"""
    global _broadcast_manager_instance
    
    if _broadcast_manager_instance is None:
        _broadcast_manager_instance = BroadcastManager()
        logger.info("✅ BroadcastManager singleton initialized")
    
    return _broadcast_manager_instance

# Crear instancia global para compatibilidad hacia atrás
broadcast_manager = get_broadcast_manager()
