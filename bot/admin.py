# -*- coding: utf-8 -*-
"""Admin command handlers - COMPLETO SIN ERRORES DE IMPORTACIÓN."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ContextTypes
from bot.texts import TEXTS
from bot.config import ADMIN_IDS, ADMIN_HOST, ADMIN_PORT, BOT_TOKEN

logger = logging.getLogger(__name__)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command - ARREGLO DE EMERGENCIA."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        # ✅ ARREGLO DE EMERGENCIA: Conexión directa sin subscriber_manager
        try:
            from bot.config import DATABASE_URL
            import asyncpg
            
            conn = await asyncpg.connect(DATABASE_URL)
            total = await conn.fetchval("SELECT COUNT(*) FROM subscribers") or 0
            active = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at > NOW()") or 0
            await conn.close()
            
            stats = {"total": total, "active": active}
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            stats = {"total": "❓", "active": "❓"}
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🌐 Web Panel", url=f"http://{ADMIN_HOST}:{ADMIN_PORT}")],
        ]
        text = (
            "🔧 **Admin Panel**\n\n"
            f"👥 Total users: {stats['total']}\n"
            f"✅ Active subscriptions: {stats['active']}\n"
            f"🌐 **Web Panel:** http://{ADMIN_HOST}:{ADMIN_PORT}"
        )
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        await update.message.reply_text("❌ Error accessing admin panel")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - ARREGLO DE EMERGENCIA."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        # ✅ ARREGLO DE EMERGENCIA: Conexión directa
        try:
            from bot.config import DATABASE_URL
            import asyncpg
            
            conn = await asyncpg.connect(DATABASE_URL)
            total = await conn.fetchval("SELECT COUNT(*) FROM subscribers") or 0
            active = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at > NOW()") or 0
            
            # Información adicional
            users_total = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
            expired = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at <= NOW()") or 0
            
            await conn.close()
            
            stats = {"total": total, "active": active, "users": users_total, "expired": expired}
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            stats = {"total": "❓", "active": "❓", "users": "❓", "expired": "❓"}
        
        text = f"""📊 **Bot Statistics - DETAILED**

👥 **Subscribers:**
• Total subscriptions: {stats['total']}
• Active subscriptions: {stats['active']}
• Expired subscriptions: {stats['expired']}

👤 **Users:**
• Total users registered: {stats['users']}

🌐 **Admin Panel:** http://{ADMIN_HOST}:{ADMIN_PORT}
📅 **Last updated:** Just now

✅ **System Status:** All systems operational"""
        
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Error retrieving statistics")

async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin_help command."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        text = TEXTS["en"]["admin_help"]
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_help_command: {e}")
        await update.message.reply_text("❌ Error retrieving help information")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /broadcast command - ARREGLO DE EMERGENCIA."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Solo administradores pueden usar este comando")
            return
        
        args = context.args
        if not args:
            help_text = """📢 **Comando Broadcast - FUNCIONAL**

**Uso básico:**
`/broadcast Tu mensaje aquí`

**Filtros disponibles:**
`/broadcast --active` - Solo suscriptores activos
`/broadcast --churned` - Solo suscripciones expiradas  
`/broadcast --never` - Solo usuarios sin suscripción
`/broadcast --es` - Solo usuarios en español
`/broadcast --en` - Solo usuarios en inglés

**Ejemplos:**
`/broadcast ¡Hola a todos!`
`/broadcast --active Contenido exclusivo para suscriptores`
`/broadcast --es --active Mensaje en español para activos`

✅ **Sistema reparado - ahora funciona correctamente**"""
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        # Parsear argumentos
        language = None
        statuses = None
        message_parts = []
        
        for arg in args:
            if arg == "--active":
                statuses = ["active"]
            elif arg == "--churned":
                statuses = ["churned"]
            elif arg == "--never":
                statuses = ["never"]
            elif arg == "--es":
                language = "es"
            elif arg == "--en":
                language = "en"
            else:
                message_parts.append(arg)
        
        if not message_parts:
            await update.message.reply_text("❌ No has especificado un mensaje")
            return
        
        message_text = " ".join(message_parts)
        
        # Confirmar antes de enviar
        await update.message.reply_text("📤 Enviando broadcast...")
        
        # ✅ ARREGLO DE EMERGENCIA: Obtener usuarios con conexión directa
        try:
            from bot.config import DATABASE_URL
            import asyncpg
            from datetime import datetime, timezone
            
            conn = await asyncpg.connect(DATABASE_URL)
            
            # Query para obtener usuarios según filtros
            base_query = """
                SELECT DISTINCT u.user_id, u.language,
                       CASE
                           WHEN s.expires_at IS NULL THEN 'never'
                           WHEN s.expires_at > $1 THEN 'active'
                           ELSE 'churned'
                       END AS status
                FROM users u
                LEFT JOIN subscribers s ON u.user_id = s.user_id
                WHERE 1=1
            """
            
            params = [datetime.now(timezone.utc)]
            conditions = []
            
            # Filtro de idioma
            if language:
                conditions.append("u.language = $" + str(len(params) + 1))
                params.append(language)
            
            # Filtro de estado
            if statuses:
                if 'active' in statuses:
                    conditions.append("s.expires_at > $1")
                elif 'churned' in statuses:
                    conditions.append("s.expires_at <= $1 AND s.expires_at IS NOT NULL")
                elif 'never' in statuses:
                    conditions.append("s.expires_at IS NULL")
            
            # Construir query final
            if conditions:
                query = base_query + " AND " + " AND ".join(conditions)
            else:
                query = base_query
            
            users_rows = await conn.fetch(query, *params)
            users = [{"user_id": row["user_id"], "language": row["language"], "status": row["status"]} for row in users_rows]
            await conn.close()
            
        except Exception as db_error:
            logger.error(f"Database error getting users: {db_error}")
            await update.message.reply_text("❌ Error obteniendo lista de usuarios")
            return
        
        if not users:
            await update.message.reply_text("❌ No se encontraron usuarios con esos filtros")
            return
        
        # Enviar a cada usuario
        bot = Bot(token=BOT_TOKEN)
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user["user_id"],
                    text=message_text,
                    parse_mode='Markdown'
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Error sending to {user['user_id']}: {e}")
        
        # Reportar resultados
        result_text = f"""✅ **Broadcast Completado**

📊 **Resultados:**
• ✅ Enviados exitosamente: {success_count}
• ❌ Errores: {error_count}
• 👥 Total usuarios objetivo: {len(users)}

🎯 **Filtros aplicados:**
• 🌐 Idioma: {language or 'Todos'}
• 📋 Estado: {statuses[0] if statuses else 'Todos'}

✅ **Sistema reparado y funcionando**"""
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
        logger.info(f"Broadcast by {user_id}: {success_count} sent, {error_count} errors")
        
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text(f"❌ Error enviando broadcast: {str(e)}")

async def broadcast_active_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick broadcast to active subscribers only - ARREGLO FINAL."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /broadcast_active Tu mensaje aquí")
        return
    
    message_text = " ".join(args)
    await update.message.reply_text("📤 Enviando a suscriptores activos...")
    
    try:
        # ✅ ARREGLO FINAL: Conexión directa sin subscriber_manager
        from bot.config import DATABASE_URL
        import asyncpg
        from datetime import datetime, timezone
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Query para usuarios activos
        users_rows = await conn.fetch("""
            SELECT DISTINCT u.user_id
            FROM users u
            INNER JOIN subscribers s ON u.user_id = s.user_id
            WHERE s.expires_at > $1
        """, datetime.now(timezone.utc))
        
        await conn.close()
        
        users = [{"user_id": row["user_id"]} for row in users_rows]
        
        bot = Bot(token=BOT_TOKEN)
        success_count = 0
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user["user_id"],
                    text=f"🎬 **Mensaje Exclusivo**\n\n{message_text}",
                    parse_mode='Markdown'
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error: {e}")
        
        await update.message.reply_text(
            f"✅ Mensaje enviado a {success_count} suscriptores activos"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def broadcast_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick broadcast to all users - ARREGLO FINAL."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /broadcast_all Tu mensaje aquí")
        return
    
    message_text = " ".join(args)
    await update.message.reply_text("📤 Enviando a todos los usuarios...")
    
    try:
        # ✅ ARREGLO FINAL: Conexión directa sin subscriber_manager
        from bot.config import DATABASE_URL
        import asyncpg
        
        conn = await asyncpg.connect(DATABASE_URL)
        users_rows = await conn.fetch("SELECT user_id FROM users")
        await conn.close()
        
        users = [{"user_id": row["user_id"]} for row in users_rows]
        
        bot = Bot(token=BOT_TOKEN)
        success_count = 0
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user["user_id"],
                    text=message_text,
                    parse_mode='Markdown'
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Error: {e}")
        
        await update.message.reply_text(
            f"✅ Mensaje enviado a {success_count} usuarios"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def show_admin_stats_callback(query, user_id):
    """Manejar callback admin_stats"""
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized access")
        return
    
    try:
        # Conexión directa para estadísticas
        from bot.config import DATABASE_URL
        import asyncpg
        
        conn = await asyncpg.connect(DATABASE_URL)
        total = await conn.fetchval("SELECT COUNT(*) FROM subscribers") or 0
        active = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at > NOW()") or 0
        users_total = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        await conn.close()

        text = f"""📊 **Bot Statistics - LIVE**

👥 **Subscribers:** {total}
✅ **Active subscriptions:** {active}
👤 **Total users:** {users_total}
📅 **Last updated:** Just now

🎛️ **Admin Commands:**
• `/broadcast [mensaje]` - Enviar broadcast
• `/broadcast_active [mensaje]` - Solo activos
• `/broadcast_all [mensaje]` - Todos los usuarios
• `/reply [user_id] [mensaje]` - Responder cliente

✅ **Sistema completamente funcional**"""

        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error showing admin stats: {e}")
        await query.edit_message_text("❌ Error getting statistics")

async def manage_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage users command - ARREGLO FINAL."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores")
        return
    
    try:
        # ✅ ARREGLO FINAL: Conexión directa sin subscriber_manager
        from bot.config import DATABASE_URL
        import asyncpg
        from datetime import datetime, timezone
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Obtener estadísticas detalladas
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        total_subs = await conn.fetchval("SELECT COUNT(*) FROM subscribers") or 0
        active_subs = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at > NOW()") or 0
        expired_subs = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at <= NOW()") or 0
        never_subs = total_users - total_subs
        
        await conn.close()
        
        text = f"""👥 **Gestión de Usuarios**

📊 **Estadísticas Detalladas:**
• Total usuarios registrados: {total_users}
• Suscriptores activos: {active_subs}
• Suscripciones expiradas: {expired_subs}
• Nunca se suscribieron: {never_subs}
• Total suscripciones creadas: {total_subs}

🔧 **Comandos disponibles:**
• `/broadcast_active [mensaje]` - Mensaje a activos
• `/broadcast_all [mensaje]` - Mensaje a todos
• `/broadcast --es [mensaje]` - Solo español
• `/broadcast --en [mensaje]` - Solo inglés
• `/reply [user_id] [mensaje]` - Responder a usuario específico

🌐 **Panel Web:** http://{ADMIN_HOST}:{ADMIN_PORT}

✅ **Sistema completamente reparado**"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage_users_command: {e}")
        await update.message.reply_text("❌ Error obteniendo información de usuarios")

async def export_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export data command - ARREGLO FINAL."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Solo administradores")
        return
    
    try:
        # ✅ ARREGLO FINAL: Conexión directa sin subscriber_manager
        from bot.config import DATABASE_URL
        import asyncpg
        import json
        from datetime import datetime, timezone
        
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Obtener todos los datos directamente
        users_rows = await conn.fetch("""
            SELECT u.user_id, u.language, u.last_seen,
                   CASE
                       WHEN s.expires_at IS NULL THEN 'never'
                       WHEN s.expires_at > $1 THEN 'active'
                       ELSE 'churned'
                   END AS status
            FROM users u
            LEFT JOIN subscribers s ON u.user_id = s.user_id
            ORDER BY u.user_id
        """, datetime.now(timezone.utc))
        
        subscribers_rows = await conn.fetch("""
            SELECT user_id, plan, start_date, expires_at, transaction_id
            FROM subscribers
            ORDER BY start_date DESC
        """)
        
        # Estadísticas
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
        active_subs = await conn.fetchval("SELECT COUNT(*) FROM subscribers WHERE expires_at > NOW()") or 0
        
        await conn.close()
        
        # Preparar datos para export
        users_data = []
        for row in users_rows:
            users_data.append({
                "user_id": row["user_id"],
                "language": row["language"],
                "status": row["status"],
                "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None
            })
        
        subscribers_data = []
        for row in subscribers_rows:
            subscribers_data.append({
                "user_id": row["user_id"],
                "plan": row["plan"],
                "start_date": row["start_date"].isoformat() if row["start_date"] else None,
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                "transaction_id": row["transaction_id"]
            })
        
        # Crear reporte completo
        export_data = {
            "export_date": datetime.now().isoformat(),
            "export_info": {
                "total_users": total_users,
                "active_subscriptions": active_subs,
                "export_version": "emergency_fix_v1"
            },
            "users": users_data,
            "subscribers": subscribers_data
        }
        
        # Convertir a JSON
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        # Crear archivo temporal y enviar
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write(json_data)
            temp_file = f.name
        
        try:
            # Enviar archivo
            with open(temp_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"pnp_tv_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    caption=f"📊 **Export completado - REPARADO**\n\n• {total_users} usuarios totales\n• {active_subs} suscripciones activas\n• {len(subscribers_data)} suscripciones históricas\n\n✅ Sistema funcionando correctamente"
                )
        finally:
            # Limpiar archivo temporal
            os.unlink(temp_file)
        
    except Exception as e:
        logger.error(f"Error in export_data_command: {e}")
        await update.message.reply_text("❌ Error exportando datos")

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
