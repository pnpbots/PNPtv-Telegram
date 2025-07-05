# -*- coding: utf-8 -*-
"""
PNP Television Bot - Sistema Completo con Recordatorios y Mejoras
================================================================
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    ContextTypes, Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler
)
import logging
import importlib
import asyncio
from bot.texts import TEXTS
from bot.config import BOT_TOKEN, ADMIN_IDS, CUSTOMER_SERVICE_CHAT_ID

# Verificar que no se ejecute directamente
if __name__ == "__main__":
    print("This module provides Telegram command handlers and isn't intended "
          "to be executed directly.\n"
          "Run 'python run_bot.py' from the project root to start the bot.")
    exit(1)

logger = logging.getLogger(__name__)

# ==========================================
# COMANDOS BÁSICOS
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with persistent state"""
    try:
        user = update.effective_user
        logger.info(f"User {user.id} ({user.full_name}) started the bot")
        
        try:
            from bot.enhanced_subscriber_manager import get_subscriber_manager
            manager = await get_subscriber_manager()
            
            # Registrar usuario con información básica
            await manager.record_user(
                user.id, 
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Verificar estado del usuario
            user_status = await manager.get_user_status(user.id)
            
            # Si el usuario ya completó el proceso, ir directo al menú principal
            if user_status.get('age_verified') and user_status.get('terms_accepted'):
                lang = user_status.get('language', 'en')
                keyboard = [
                    [InlineKeyboardButton(TEXTS[lang]["plans"], callback_data="show_plans")],
                    [InlineKeyboardButton("📊 My Subscription", callback_data="subscription_status")],
                    [InlineKeyboardButton(TEXTS[lang]["policies_menu"], callback_data="policies")],
                    [InlineKeyboardButton(TEXTS[lang]["contact"], callback_data="contact")]
                ]
                
                if user.id in ADMIN_IDS:
                    keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_stats")])
                
                text = f"{TEXTS[lang]['welcome']}\n\n{TEXTS[lang]['welcome_desc']}"
                
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                return
                
        except Exception as e:
            logger.error(f"Failed to record user {user.id}: {e}")
        
        # Proceso inicial de selección de idioma
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
                InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")
            ]
        ]
        
        welcome_text = (
            "🎬 **Welcome to PNP Television Bot Ultimate!**\n"
            "Please choose your language:\n\n"
            "🎬 **¡Bienvenido a PNP Television Bot Ultimate!**\n"
            "Por favor elige tu idioma:"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("An error occurred. Please try again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        user_id = update.effective_user.id
        
        if user_id in ADMIN_IDS:
            help_text = """🎬 **PNP Television Bot Ultimate - Admin**

**👤 User Commands:**
/start - Start the bot and select language
/help - Show this help message
/plans - View subscription plans
/status - Check subscription status

**🔧 Admin Commands:**
/admin - Access admin panel
/stats - View bot statistics
/broadcast - Send broadcast message
/reply [user_id] [message] - Reply to customer
/manage_users - Manage user subscriptions
/export_data - Export user data

**🌐 Admin Panel:** http://localhost:8080
**📊 Features:** Auto channel management, broadcast system, customer service

**📧 Support:** support@pnptv.app"""
        else:
            help_text = """🎬 **PNP Television Bot Ultimate**

**Available Commands:**
/start - Start the bot and select language
/help - Show this help message
/plans - View subscription plans
/status - Check subscription status

**Features:**
✅ Multiple subscription plans
✅ Secure payment processing  
✅ Real-time channel access
✅ Multi-language support
✅ 24/7 customer service

**💬 Need Help?**
Just send any message to this bot and our support team will contact you!

**📧 Support Email:** support@pnptv.app
**⏱️ Response Time:** 24-48 hours"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text("Error showing help")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check subscription status"""
    try:
        user_id = update.effective_user.id
        from bot.enhanced_subscriber_manager import get_subscriber_manager
        
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        
        if user_status['subscription']:
            sub = user_status['subscription']
            status = user_status['status']
            
            if status == 'active':
                status_emoji = "✅"
                status_text = "Active Subscription"
                expires_text = f"⏰ **Expires:** {sub['expires_at'].strftime('%Y-%m-%d %H:%M')} UTC"
                extra_text = "\n🎬 You have access to all premium channels!"
            else:
                status_emoji = "⚠️"
                status_text = "Expired Subscription"
                expires_text = f"⏰ **Expired:** {sub['expires_at'].strftime('%Y-%m-%d %H:%M')} UTC"
                extra_text = "\n💡 Renew your subscription to regain access!"
            
            response = f"""📊 **Your Subscription Status**

{status_emoji} **Status:** {status_text}
💎 **Plan:** {sub['plan']}
📅 **Started:** {sub['start_date'].strftime('%Y-%m-%d')}
{expires_text}
🌐 **Language:** {user_status['language'].upper()}{extra_text}

Use /plans to see available subscriptions."""
        else:
            response = f"""📊 **Your Status**

❌ **Status:** No Active Subscription
🌐 **Language:** {user_status['language'].upper()}
📅 **Member since:** {user_status['last_seen'].strftime('%Y-%m-%d') if user_status['last_seen'] else 'Recently'}

💡 **Ready to start?** Use /plans to see our subscription options!"""
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.message.reply_text("❌ Error checking status. Please try again.")

# ==========================================
# BROADCAST SYSTEM
# ==========================================

# Estados de conversación para broadcast
BROADCAST_TEXT, BROADCAST_AUDIENCE, BROADCAST_LANGUAGE, BROADCAST_CONFIRM = range(4)

broadcast_data = {}  # Almacenar datos del broadcast en progreso

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar proceso de broadcast - /broadcast"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores pueden usar este comando")
        return ConversationHandler.END
    
    # Inicializar datos del broadcast
    broadcast_data[user_id] = {
        'text': None,
        'photo': None,
        'video': None,
        'animation': None,
        'audience': 'all',
        'language': None
    }
    
    await update.message.reply_text(
        "📢 **Sistema de Broadcast Activado**\n\n"
        "Envía el mensaje que quieres difundir:\n"
        "• 📝 Texto simple (con formato Markdown)\n"
        "• 📸 Foto con caption\n"
        "• 🎥 Video con caption\n"
        "• 🎬 GIF con caption\n\n"
        "💡 **Tip:** Usa formato Markdown para texto enriquecido\n"
        "Ejemplo: **negrita**, *cursiva*, `código`\n\n"
        "Usa /cancel para cancelar",
        parse_mode='Markdown'
    )
    
    return BROADCAST_TEXT

async def broadcast_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibir contenido del broadcast"""
    user_id = update.effective_user.id
    
    if update.message.text:
        broadcast_data[user_id]['text'] = update.message.text
        content_type = "📝 Texto"
    elif update.message.photo:
        broadcast_data[user_id]['photo'] = update.message.photo[-1].file_id
        broadcast_data[user_id]['text'] = update.message.caption
        content_type = "📸 Foto"
    elif update.message.video:
        broadcast_data[user_id]['video'] = update.message.video.file_id
        broadcast_data[user_id]['text'] = update.message.caption
        content_type = "🎥 Video"
    elif update.message.animation:
        broadcast_data[user_id]['animation'] = update.message.animation.file_id
        broadcast_data[user_id]['text'] = update.message.caption
        content_type = "🎬 GIF"
    else:
        await update.message.reply_text("❌ Tipo de contenido no soportado. Intenta de nuevo.")
        return BROADCAST_TEXT
    
    # Mostrar opciones de audiencia
    keyboard = [
        [InlineKeyboardButton("🌍 Todos los usuarios", callback_data="audience_all")],
        [InlineKeyboardButton("✅ Solo suscriptores activos", callback_data="audience_active")],
        [InlineKeyboardButton("⚠️ Suscripciones expiradas", callback_data="audience_churned")],
        [InlineKeyboardButton("❌ Nunca compraron", callback_data="audience_never")],
        [InlineKeyboardButton("🆕 Usuarios nuevos (7 días)", callback_data="audience_new")]
    ]
    
    await update.message.reply_text(
        f"✅ **Contenido recibido:** {content_type}\n\n"
        "🎯 **Selecciona la audiencia:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return BROADCAST_AUDIENCE

async def broadcast_audience_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de audiencia"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    audience = query.data.replace("audience_", "")
    broadcast_data[user_id]['audience'] = audience
    
    audience_names = {
        'all': '🌍 Todos los usuarios',
        'active': '✅ Solo suscriptores activos',
        'churned': '⚠️ Suscripciones expiradas',
        'never': '❌ Nunca compraron',
        'new': '🆕 Usuarios nuevos'
    }
    
    # Mostrar opciones de idioma
    keyboard = [
        [InlineKeyboardButton("🌍 Todos los idiomas", callback_data="lang_all")],
        [InlineKeyboardButton("🇺🇸 Solo inglés", callback_data="lang_en")],
        [InlineKeyboardButton("🇪🇸 Solo español", callback_data="lang_es")]
    ]
    
    await query.edit_message_text(
        f"✅ **Audiencia seleccionada:** {audience_names[audience]}\n\n"
        "🌐 **Selecciona el idioma:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return BROADCAST_LANGUAGE

async def broadcast_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de idioma"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    language = query.data.replace("lang_", "")
    
    if language != "all":
        broadcast_data[user_id]['language'] = language
    
    # Calcular audiencia estimada
    try:
        from bot.enhanced_subscriber_manager import get_subscriber_manager
        
        manager = await get_subscriber_manager()
        
        # Filtros para la consulta
        lang_filter = None if language == "all" else language
        status_filter = None
        
        if broadcast_data[user_id]['audience'] == 'active':
            status_filter = ['active']
        elif broadcast_data[user_id]['audience'] == 'churned':
            status_filter = ['churned']
        elif broadcast_data[user_id]['audience'] == 'never':
            status_filter = ['never']
        
        users = await manager.get_users(language=lang_filter, statuses=status_filter)
        audience_count = len(users)
        
    except Exception as e:
        logger.error(f"Error calculating audience: {e}")
        audience_count = "❓"
    
    # Mostrar resumen y confirmación
    audience_names = {
        'all': '🌍 Todos los usuarios',
        'active': '✅ Solo suscriptores activos',
        'churned': '⚠️ Suscripciones expiradas', 
        'never': '❌ Nunca compraron',
        'new': '🆕 Usuarios nuevos'
    }
    
    language_names = {
        'all': '🌍 Todos los idiomas',
        'en': '🇺🇸 Solo inglés',
        'es': '🇪🇸 Solo español'
    }
    
    content_preview = broadcast_data[user_id]['text']
    if content_preview and len(content_preview) > 100:
        content_preview = content_preview[:100] + "..."
    
    summary = f"""📢 **Resumen del Broadcast**

📝 **Contenido:** {content_preview or '[Multimedia]'}
🎯 **Audiencia:** {audience_names[broadcast_data[user_id]['audience']]}
🌐 **Idioma:** {language_names[language]}
👥 **Usuarios estimados:** {audience_count}

⚠️ **¿Confirmas el envío?**
Este mensaje se enviará inmediatamente a todos los usuarios seleccionados."""

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar y Enviar", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_broadcast")]
    ]
    
    await query.edit_message_text(
        summary,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return BROADCAST_CONFIRM

async def broadcast_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirmar y enviar broadcast"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "cancel_broadcast":
        await query.edit_message_text("❌ Broadcast cancelado")
        if user_id in broadcast_data:
            del broadcast_data[user_id]
        return ConversationHandler.END
    
    # Ejecutar broadcast
    try:
        data = broadcast_data[user_id]
        
        # Configurar filtros
        lang_filter = data.get('language')
        status_filter = None
        
        if data['audience'] == 'active':
            status_filter = ['active']
        elif data['audience'] == 'churned':
            status_filter = ['churned']
        elif data['audience'] == 'never':
            status_filter = ['never']
        
        await query.edit_message_text("📤 **Enviando broadcast...**\n\nEsto puede tomar unos momentos.")
        
        # Enviar broadcast usando el sistema existente
        from bot.broadcast_manager import broadcast_manager
        
        await broadcast_manager.send(
            text=data['text'],
            photo=data.get('photo'),
            video=data.get('video'),
            animation=data.get('animation'),
            language=lang_filter,
            statuses=status_filter,
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            "✅ **Broadcast enviado exitosamente!**\n\n"
            "📊 Todos los usuarios de la audiencia seleccionada han recibido el mensaje."
        )
        
        logger.info(f"Broadcast sent by admin {user_id} to audience: {data['audience']}, language: {lang_filter}")
        
    except Exception as e:
        logger.error(f"Error sending broadcast: {e}")
        await query.edit_message_text(f"❌ **Error enviando broadcast:**\n\n{str(e)}")
    
    # Limpiar datos
    if user_id in broadcast_data:
        del broadcast_data[user_id]
    
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancelar broadcast"""
    user_id = update.effective_user.id
    if user_id in broadcast_data:
        del broadcast_data[user_id]
    
    await update.message.reply_text("❌ Broadcast cancelado")
    return ConversationHandler.END

# ==========================================
# CUSTOMER SERVICE SYSTEM
# ==========================================

async def handle_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de usuarios como solicitudes de servicio al cliente"""
    
    # Ignorar mensajes de comandos
    if update.message.text and update.message.text.startswith('/'):
        return
    
    user = update.effective_user
    message = update.message
    
    try:
        # Enviar al chat de soporte si está configurado
        if CUSTOMER_SERVICE_CHAT_ID:
            # Crear mensaje para el equipo de soporte
            support_message = f"""🔔 **Nueva Consulta de Cliente**

👤 **Usuario:** {user.full_name}
👤 **Username:** @{user.username or 'N/A'}
🆔 **ID:** `{user.id}`
📅 **Fecha:** {message.date.strftime('%Y-%m-%d %H:%M:%S')} UTC

💬 **Mensaje:**
{message.text or message.caption or '[Archivo multimedia]'}

---
**Para responder usa:** `/reply {user.id} tu_respuesta_aqui`"""

            # Enviar al chat de soporte
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=CUSTOMER_SERVICE_CHAT_ID,
                text=support_message,
                parse_mode='Markdown'
            )
        
        # Confirmar al usuario
        await message.reply_text(
            "✅ **Mensaje recibido**\n\n"
            "Nuestro equipo de soporte ha sido notificado y te contactará pronto.\n\n"
            "⏱️ **Tiempo de respuesta:** 24-48 horas\n"
            "📧 **Email alternativo:** support@pnptv.app\n"
            "💬 **Tip:** Puedes enviar más detalles si es necesario",
            parse_mode='Markdown'
        )
        
        logger.info(f"Customer service message from {user.id} ({user.username}): {message.text[:50] if message.text else 'multimedia'}...")
        
    except Exception as e:
        logger.error(f"Error handling customer message: {e}")
        await message.reply_text(
            "❌ **Error procesando tu mensaje**\n\n"
            "Por favor contacta directamente a: support@pnptv.app"
        )

async def reply_to_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responder a un cliente - /reply [user_id] [mensaje]"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores pueden usar este comando")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "📝 **Uso del comando /reply**\n\n"
            "**Formato:** `/reply [user_id] [mensaje]`\n\n"
            "**Ejemplo:**\n"
            "`/reply 123456789 Hola, gracias por contactarnos. ¿En qué puedo ayudarte?`",
            parse_mode='Markdown'
        )
        return
    
    try:
        customer_id = int(args[0])
        response_message = " ".join(args[1:])
        
        # Enviar respuesta al cliente
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=customer_id,
            text=f"👨‍💼 **Soporte PNP Television**\n\n{response_message}\n\n"
                 f"¿Necesitas más ayuda? Solo escribe tu pregunta.",
            parse_mode='Markdown'
        )
        
        # Confirmar al admin
        await update.message.reply_text(
            f"✅ **Respuesta enviada exitosamente**\n\n"
            f"👤 **Cliente:** {customer_id}\n"
            f"💬 **Mensaje:** {response_message[:100]}{'...' if len(response_message) > 100 else ''}"
        )
        
        logger.info(f"Admin {user_id} replied to customer {customer_id}")
        
    except ValueError:
        await update.message.reply_text("❌ **Error:** ID de usuario inválido. Debe ser un número.")
    except Exception as e:
        logger.error(f"Error replying to customer: {e}")
        await update.message.reply_text(f"❌ **Error enviando respuesta:**\n\n{str(e)}")

# ==========================================
# SMART IMPORT SYSTEM
# ==========================================

def smart_import_function(module_name, function_name):
    """Safely import a function if it exists"""
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, function_name):
            func = getattr(module, function_name)
            if callable(func):
                return func
        return None
    except Exception as e:
        logger.warning(f"Could not import {function_name} from {module_name}: {e}")
        return None

# ==========================================
# HANDLER REGISTRATION
# ==========================================

async def register_smart_handlers(application: Application):
    """Register all handlers intelligently"""
    try:
        logger.info("🚀 Smart handler registration starting...")
        
        # ===== COMANDOS BÁSICOS =====
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        logger.info("✅ Basic commands registered")
        
        # ===== SISTEMA DE BROADCAST =====
        broadcast_conversation = ConversationHandler(
            entry_points=[CommandHandler("broadcast", broadcast_command)],
            states={
                BROADCAST_TEXT: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_text_handler)],
                BROADCAST_AUDIENCE: [CallbackQueryHandler(broadcast_audience_callback, pattern="^audience_")],
                BROADCAST_LANGUAGE: [CallbackQueryHandler(broadcast_language_callback, pattern="^lang_")],
                BROADCAST_CONFIRM: [CallbackQueryHandler(broadcast_confirm_callback, pattern="^(confirm|cancel)_broadcast$")]
            },
            fallbacks=[CommandHandler("cancel", cancel_broadcast)]
        )
        application.add_handler(broadcast_conversation)
        logger.info("✅ Broadcast conversation handler registered")
        
        # ===== SERVICIO AL CLIENTE =====
        application.add_handler(CommandHandler("reply", reply_to_customer))
        logger.info("✅ Customer service reply handler registered")
        
        # ===== COMANDOS DE ADMINISTRADOR =====
        admin_functions = [
            ("bot.admin", "admin_command", "admin"),
            ("bot.admin", "stats_command", "stats"), 
            ("bot.admin", "admin_help_command", "admin_help")
        ]
        
        admin_count = 0
        for module, func_name, command in admin_functions:
            func = smart_import_function(module, func_name)
            if func:
                application.add_handler(CommandHandler(command, func))
                admin_count += 1
        
        if admin_count > 0:
            logger.info(f"✅ Admin commands registered: {admin_count}")
        
        # ===== COMANDO DE PLANES =====
        plans_func = smart_import_function("bot.plans", "plans_command")
        if plans_func:
            application.add_handler(CommandHandler("plans", plans_func))
            logger.info("✅ Plans command registered")
        else:
            async def simple_plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
                await update.message.reply_text(
                    "💎 **Subscription Plans**\n\n"
                    "Use the /start command and navigate through the menus to see available plans.\n\n"
                    "Or visit our admin panel for more options."
                )
            application.add_handler(CommandHandler("plans", simple_plans_command))
            logger.info("✅ Fallback plans command registered")
        
        # ===== CALLBACKS INLINE =====
        callback_func = smart_import_function("bot.callbacks", "handle_callback")
        if callback_func:
            application.add_handler(CallbackQueryHandler(callback_func))
            logger.info("✅ Inline callback handler registered")
        else:
            async def simple_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
                query = update.callback_query
                await query.answer()
                if query.data.startswith("lang_"):
                    lang = query.data.split("_")[1]
                    await query.edit_message_text(f"Language set to: {'English' if lang == 'en' else 'Español'}")
                else:
                    await query.edit_message_text("This feature is being updated. Please use /start")
            
            application.add_handler(CallbackQueryHandler(simple_callback_handler))
            logger.info("✅ Fallback callback handler registered")
        
        # ===== SISTEMA DE SERVICIO AL CLIENTE (DEBE IR AL FINAL) =====
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                handle_customer_message
            )
        )
        logger.info("✅ Customer service message handler registered")
        
        # ===== RESUMEN =====
        total_handlers = sum(len(group) for group in application.handlers.values())
        logger.info(f"🎉 Smart registration complete! Total handlers: {total_handlers}")
        
        return total_handlers
        
    except Exception as e:
        logger.error(f"❌ Error in smart handler registration: {e}")
        return 0

# ==========================================
# AUTOMATION TASKS
# ==========================================

async def start_automation_tasks():
    """Iniciar tareas de automatización en background con recordatorios"""
    try:
        logger.info("🤖 Starting automation tasks...")
        
        from bot.enhanced_subscriber_manager import get_subscriber_manager
        
        manager = await get_subscriber_manager()
        
        async def automation_loop():
            while True:
                try:
                    logger.info("🔄 Running automated subscription check...")
                    
                    # Verificar suscripciones expiradas
                    expired_users = await manager.check_expired_subscriptions()
                    
                    if expired_users:
                        logger.info(f"📊 Processed {len(expired_users)} expired subscriptions")
                    else:
                        logger.info("📊 No expired subscriptions found")
                    
                    # Verificar recordatorios de renovación
                    reminded_users = await manager.check_renewal_reminders()
                    
                    if reminded_users:
                        logger.info(f"📧 Sent {len(reminded_users)} renewal reminders")
                    else:
                        logger.info("📧 No renewal reminders needed")
                    
                    # Esperar 1 hora antes del siguiente check
                    await asyncio.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"❌ Error in automation loop: {e}")
                    await asyncio.sleep(300)  # Esperar 5 minutos si hay error
        
        # Iniciar loop de automatización
        asyncio.create_task(automation_loop())
        logger.info("✅ Automation tasks started successfully")
        
    except Exception as e:
        logger.error(f"❌ Error starting automation tasks: {e}")

# ==========================================
# MAIN FUNCTION
# ==========================================

async def main():
    """Main function to run the bot with all features"""
    try:
        from bot.config import BOT_TOKEN
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not configured!")
            raise ValueError("BOT_TOKEN must be set in .env file")
        
        logger.info("🚀 Starting PNP Television Bot Ultimate...")
        
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Registrar todos los handlers
        handler_count = await register_smart_handlers(application)
        
        if handler_count == 0:
            logger.error("❌ No handlers could be registered!")
            return
        
        # Iniciar tareas de automatización
        await start_automation_tasks()
        
        logger.info(f"🎉 Bot starting with {handler_count} handlers...")
        logger.info("🔄 Features active: Auto channel management, broadcast system, customer service, renewal reminders")
        
        # Inicializar y ejecutar el bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("✅ Bot is now running and ready to receive messages!")
        
        # Mantener el bot corriendo
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise

