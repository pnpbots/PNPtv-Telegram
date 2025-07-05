# -*- coding: utf-8 -*-
"""
SISTEMA DE BROADCAST - ANÁLISIS COMPLETO
=========================================

El sistema de broadcast está en bot/broadcast_manager.py
Permite enviar mensajes masivos a usuarios filtrados por idioma y estado.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging
from telegram import Bot
from bot.subscriber_manager import subscriber_manager
from bot.config import BOT_TOKEN

logger = logging.getLogger(__name__)

class BroadcastManager:
    """
    GESTOR DE BROADCASTS
    ====================
    
    Características principales:
    - Envío de mensajes masivos
    - Filtrado por idioma y estado de suscripción
    - Programación de mensajes (hasta 72 horas)
    - Límite de 12 mensajes programados por día
    - Soporte para texto, fotos, videos, GIFs
    """

    def __init__(self, bot: Bot | None = None):
        self.bot = bot or Bot(token=BOT_TOKEN)
        self.scheduled: List[tuple[datetime, asyncio.Task]] = []  # Mensajes programados

    # ==========================================
    # ENVÍO INMEDIATO DE BROADCASTS
    # ==========================================
    
    async def send(
        self,
        text: Optional[str] = None,
        parse_mode: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        animation: Optional[str] = None,
        language: Optional[str] = None,        # Filtro: 'en', 'es', None (todos)
        statuses: Optional[List[str]] = None,  # Filtro: ['active'], ['churned'], etc.
    ) -> None:
        """
        ENVÍO MASIVO INMEDIATO
        ======================
        
        Ejemplos de uso:
        
        # A todos los usuarios:
        await broadcast_manager.send(text="¡Mensaje para todos!")
        
        # Solo usuarios en español:
        await broadcast_manager.send(
            text="¡Hola usuarios en español!",
            language="es"
        )
        
        # Solo usuarios con suscripción activa:
        await broadcast_manager.send(
            text="Contenido exclusivo para suscriptores",
            statuses=["active"]
        )
        
        # Usuarios activos que hablan inglés:
        await broadcast_manager.send(
            text="Exclusive content for English subscribers",
            language="en",
            statuses=["active"]
        )
        """
        
        # Obtiene usuarios filtrados desde la base de datos
        users = await subscriber_manager.get_users(language=language, statuses=statuses)
        
        for user in users:
            try:
                user_id = user["user_id"]
                
                # Envía según el tipo de contenido
                if photo:
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=text,
                        parse_mode=parse_mode,
                    )
                elif video:
                    await self.bot.send_video(
                        chat_id=user_id,
                        video=video,
                        caption=text,
                        parse_mode=parse_mode,
                    )
                elif animation:  # GIFs
                    await self.bot.send_animation(
                        chat_id=user_id,
                        animation=animation,
                        caption=text,
                        parse_mode=parse_mode,
                    )
                elif text:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode=parse_mode,
                    )
                    
            except Exception as exc:
                # Si el usuario bloqueó el bot, ignora el error
                logger.error("Error enviando broadcast a %s: %s", user_id, exc)

    # ==========================================
    # PROGRAMACIÓN DE BROADCASTS
    # ==========================================
    
    def schedule(
        self,
        when: datetime,  # Cuándo enviar (máximo 72 horas)
        *,
        text: Optional[str] = None,
        parse_mode: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        animation: Optional[str] = None,
        language: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> None:
        """
        PROGRAMAR BROADCAST
        ===================
        
        Ejemplo de uso:
        
        # Programar para mañana a las 10 AM
        tomorrow_10am = datetime.now(timezone.utc) + timedelta(days=1)
        tomorrow_10am = tomorrow_10am.replace(hour=10, minute=0, second=0)
        
        broadcast_manager.schedule(
            when=tomorrow_10am,
            text="¡Buenos días! Nuevo contenido disponible",
            language="es",
            statuses=["active"]
        )
        """
        
        now = datetime.now(timezone.utc)
        
        # Validaciones de tiempo
        if when < now or when > now + timedelta(hours=72):
            raise ValueError("El tiempo de broadcast debe estar dentro de 72 horas")
        
        # Límite de mensajes programados por día
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(hours=24)
        count = sum(1 for (t, _) in self.scheduled if day_start <= t < day_end)
        
        if count >= 12:
            raise ValueError("Máximo 12 mensajes programados por 24h")

        # Crea tarea asíncrona para el envío
        async def _task():
            delay = (when - datetime.now(timezone.utc)).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Ejecuta el envío cuando llegue el momento
            await self.send(
                text=text,
                parse_mode=parse_mode,
                photo=photo,
                video=video,
                animation=animation,
                language=language,
                statuses=statuses,
            )

        # Programa la tarea
        task = asyncio.create_task(_task())
        self.scheduled.append((when, task))

        # Auto-limpieza cuando termina
        def _cleanup(fut: asyncio.Task) -> None:
            self.scheduled = [
                (w, t) for (w, t) in self.scheduled if t is not fut
            ]

        task.add_done_callback(_cleanup)

# ==========================================
# INSTANCIA GLOBAL
# ==========================================

broadcast_manager = BroadcastManager()

# ==========================================
# COMANDOS DE ADMINISTRADOR (Hipotéticos)
# ==========================================

"""
Aunque no están implementados en el código actual, 
estos serían comandos típicos para administradores:

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''
    Comando: /broadcast
    
    Uso:
    /broadcast Hola a todos los usuarios
    /broadcast --lang es Mensaje en español
    /broadcast --status active Solo para suscriptores activos
    '''
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores")
        return
    
    # Parsear argumentos del mensaje
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /broadcast <mensaje>")
        return
    
    # Lógica para parsear filtros y enviar
    message = " ".join(args)
    await broadcast_manager.send(text=message)
    await update.message.reply_text("✅ Broadcast enviado")

async def schedule_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''
    Comando: /schedule_broadcast
    
    Uso:
    /schedule_broadcast 2024-12-25 10:00 Feliz Navidad!
    '''
    # Lógica para programar mensajes
    pass

async def broadcast_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''
    Comando: /broadcast_stats
    
    Muestra estadísticas de broadcasts enviados
    '''
    # Mostrar mensajes programados, enviados, etc.
    pass
"""

# ==========================================
# EJEMPLOS DE USO PRÁCTICO
# ==========================================

"""
CASOS DE USO TÍPICOS:

1. NOTIFICAR NUEVO CONTENIDO:
   await broadcast_manager.send(
       text="🎬 ¡Nuevo video disponible en el canal!",
       statuses=["active"]
   )

2. RECORDATORIO DE VENCIMIENTO:
   # Obtener usuarios que vencen en 3 días
   await broadcast_manager.send(
       text="⚠️ Tu suscripción vence en 3 días. ¡Renueva ahora!",
       # Filtro personalizado requerido en la lógica
   )

3. PROMOCIONES SEGMENTADAS:
   # Para usuarios sin suscripción
   await broadcast_manager.send(
       text="💎 ¡Oferta especial! 50% OFF en tu primera suscripción",
       statuses=["never", "churned"]
   )

4. MENSAJE MULTIIDIOMA:
   # Español
   await broadcast_manager.send(
       text="🎉 ¡Celebramos 1000 suscriptores!",
       language="es"
   )
   
   # Inglés
   await broadcast_manager.send(
       text="🎉 Celebrating 1000 subscribers!",
       language="en"
   )

5. CONTENIDO CON IMAGEN:
   await broadcast_manager.send(
       photo="https://ejemplo.com/imagen.jpg",
       text="📸 Sneak peek del próximo contenido",
       statuses=["active"]
   )
"""