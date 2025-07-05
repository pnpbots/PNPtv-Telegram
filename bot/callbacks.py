        keyboard = [
            [InlineKeyboardButton("💳 Pay Securely with Bold.co", url=payment_url)],
            [InlineKeyboardButton("🔄 Choose Different Plan", callback_data="show_plans")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Log de selección de plan para analytics
        logger.info(f"Usuario {user_id} seleccionó plan {plan_info['name']} ({plan_info['price']})")
        
    except Exception as e:
        logger.error(f"Error en selección de plan para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error procesando selección de plan.\n"
            "Por favor intenta de nuevo o contacta soporte."
        )

async def show_subscription_status(query, user_id, data):
    """Mostrar estado de suscripción con información detallada"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        status = user_status['status']
        
        # Emojis y textos por estado
        status_info = {
            'active': ('✅', 'Active Subscription', '🎬 Enjoying premium content!'),
            'churned': ('⚠️', 'Expired Subscription', '💡 Renew to regain access!'), 
            'never': ('❌', 'No Subscription', '🚀 Ready to start your journey?')
        }
        
        emoji, status_text, action_text = status_info.get(status, ('❓', 'Unknown Status', ''))
        
        if status == 'active' and user_status['subscription']:
            sub = user_status['subscription']
            expires_at = sub['expires_at']
            
            # Calcular días restantes
            from datetime import datetime, timezone
            days_remaining = (expires_at - datetime.now(timezone.utc)).days
            
            # Obtener información de canales activos
            active_channels = [ch for ch in user_status['channel_access'] if ch['revoked_at'] is None]
            
            # Información de facturación
            billing_info = ""
            if sub.get('payment_amount'):
                billing_info = f"\n💰 **Amount paid:** ${sub['payment_amount']:.2f} USD"
            if sub.get('transaction_id'):
                billing_info += f"\n🧾 **Transaction:** {sub['transaction_id'][:20]}..."
            
            text = f"""📊 **Your Subscription Status**

{emoji} **Status:** {status_text}
💎 **Plan:** {sub['plan']}
📅 **Started:** {sub['start_date'].strftime('%Y-%m-%d')}
⏰ **Expires:** {expires_at.strftime('%Y-%m-%d %H:%M')} UTC
⏳ **Days remaining:** {days_remaining} days

📺 **Active channels:** {len(active_channels)}
{billing_info}

{action_text}

💡 **Tip:** Renew before expiration to avoid service interruption."""

            keyboard = [
                [InlineKeyboardButton("🔄 Renew Subscription", callback_data="show_plans")],
                [InlineKeyboardButton("📧 Contact Support", callback_data="contact")]
            ]
            
        elif status == 'churned' and user_status['subscription']:
            sub = user_status['subscription']
            expired_date = sub['expires_at']
            
            # Calcular días desde expiración
            days_expired = (datetime.now(timezone.utc) - expired_date).days
            
            text = f"""📊 **Your Subscription Status**

{emoji} **Status:** {status_text}
💎 **Previous plan:** {sub['plan']}
📅 **Expired:** {expired_date.strftime('%Y-%m-%d %H:%M')} UTC
⏳ **Days ago:** {days_expired} days

❌ **Channel access:** Revoked
📞 **Support:** Available 24/7

{action_text}

🎯 **Special offer:** Check our plans for returning customers!"""

            keyboard = [
                [InlineKeyboardButton("💎 View Plans", callback_data="show_plans")],
                [InlineKeyboardButton("📧 Contact Support", callback_data="contact")]
            ]
            
        else:  # never subscribed
            text = f"""📊 **Your Subscription Status**

{emoji} **Status:** {status_text}
📅 **Member since:** {user_status.get('last_seen', datetime.now()).strftime('%Y-%m-%d')}
🌐 **Language:** {lang.upper()}

{action_text}

🎬 **What you're missing:**
• 200+ exclusive premium videos
• Multiple premium channels  
• Virtual events and live content
• Priority customer support

💰 **Plans starting at just $14.99!**"""

            keyboard = [
                [InlineKeyboardButton("💎 View Subscription Plans", callback_data="show_plans")],
                [InlineKeyboardButton("❓ Learn More", callback_data="help")]
            ]
        
        keyboard.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="main_menu")])
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error verificando estado de suscripción para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error verificando estado de suscripción.\n"
            "Por favor intenta de nuevo."
        )

async def show_policies(query, user_id, data):
    """Menú de políticas mejorado"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["terms_label"], callback_data="terms")],
            [InlineKeyboardButton(TEXTS[lang]["privacy_label"], callback_data="privacy")],
            [InlineKeyboardButton(TEXTS[lang]["refund_label"], callback_data="refund")],
            [InlineKeyboardButton("📞 Contact Legal", callback_data="contact")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="main_menu")]
        ]
        
        policy_text = TEXTS[lang]["policies_menu"]
        additional_info = "\n\n📋 **Legal Information:**\n" \
                         "• Terms updated: December 2024\n" \
                         "• GDPR compliant\n" \
                         "• Adult content service\n" \
                         "• Secure payment processing"
        
        await query.edit_message_text(
            text=policy_text + additional_info,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando políticas para {user_id}: {e}")
        await query.edit_message_text("❌ Error cargando políticas.")

async def show_terms(query, user_id, data):
    """Términos y condiciones completos"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton("📧 Legal Questions", callback_data="contact")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="policies")]
        ]
        
        terms_text = TEXTS[lang]["terms_content"]
        
        # Agregar información adicional
        additional_terms = "\n\n**📅 Last Updated:** December 2024\n" \
                          "**⚖️ Jurisdiction:** International\n" \
                          "**📧 Legal Contact:** legal@pnptv.app"
        
        full_text = terms_text + additional_terms
        
        # Verificar límite de caracteres de Telegram
        if len(full_text) > 4096:
            full_text = terms_text[:4000] + "\n\n[...continued on website...]" + additional_terms
        
        await query.edit_message_text(
            text=full_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando términos para {user_id}: {e}")
        await query.edit_message_text("❌ Error cargando términos.")

async def show_privacy(query, user_id, data):
    """Política de privacidad detallada"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete My Data", callback_data="delete_data_request")],
            [InlineKeyboardButton("📧 Privacy Questions", callback_data="contact")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="policies")]
        ]
        
        privacy_text = TEXTS[lang]["privacy_content"]
        
        # Agregar información específica
        gdpr_info = "\n\n**🔐 Your Privacy Rights:**\n" \
                   "• Right to access your data\n" \
                   "• Right to rectification\n" \
                   "• Right to erasure\n" \
                   "• Right to data portability\n\n" \
                   "**📧 Privacy Officer:** privacy@pnptv.app"
        
        full_text = privacy_text + gdpr_info
        
        await query.edit_message_text(
            text=full_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando privacidad para {user_id}: {e}")
        await query.edit_message_text("❌ Error cargando política de privacidad.")

async def show_refund(query, user_id, data):
    """Política de reembolsos clara"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton("💬 Request Refund", callback_data="contact")],
            [InlineKeyboardButton("❓ Refund Questions", callback_data="contact")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="policies")]
        ]
        
        refund_text = TEXTS[lang]["refund_content"]
        
        # Agregar proceso detallado
        process_info = "\n\n**📋 Refund Process:**\n" \
                      "1. Contact support within 48 hours\n" \
                      "2. Provide transaction ID\n" \
                      "3. Explain technical issue\n" \
                      "4. Wait 3-5 business days for review\n\n" \
                      "**⏱️ Processing Time:** 5-7 business days\n" \
                      "**💳 Refund Method:** Original payment method"
        
        full_text = refund_text + process_info
        
        await query.edit_message_text(
            text=full_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando reembolsos para {user_id}: {e}")
        await query.edit_message_text("❌ Error cargando política de reembolsos.")

async def show_contact(query, user_id, data):
    """Información de contacto completa"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        if lang == 'es':
            contact_text = """📞 **Información de Contacto**

**📧 Email Principal:** support@pnptv.app
**⚡ Email Urgencias:** urgent@pnptv.app
**⚖️ Email Legal:** legal@pnptv.app

**🕐 Horarios de Atención:**
• Lunes - Viernes: 9:00 AM - 6:00 PM EST
• Sábado - Domingo: 12:00 PM - 4:00 PM EST
• Urgencias: 24/7 (email únicamente)

**📱 Cómo obtener ayuda:**
1. Envía cualquier mensaje a este bot
2. Incluye tu ID de usuario: `{user_id}`
3. Describe tu problema claramente
4. Adjunta capturas si es necesario

**🚨 Para Emergencias:**
• Problemas de facturación: urgent@pnptv.app
• Acceso bloqueado: support@pnptv.app
• Problemas legales: legal@pnptv.app

**⏱️ Tiempo de Respuesta:**
• Consultas generales: 24-48 horas
• Problemas técnicos: 12-24 horas
• Emergencias: 2-6 horas

¡Estamos aquí para ayudarte! 🎬"""
        else:
            contact_text = f"""📞 **Contact Information**

**📧 Main Support:** support@pnptv.app
**⚡ Urgent Issues:** urgent@pnptv.app
**⚖️ Legal Matters:** legal@pnptv.app

**🕐 Business Hours:**
• Monday - Friday: 9:00 AM - 6:00 PM EST
• Saturday - Sunday: 12:00 PM - 4:00 PM EST
• Emergencies: 24/7 (email only)

**📱 How to get help:**
1. Send any message to this bot
2. Include your user ID: `{user_id}`
3. Describe your issue clearly
4. Attach screenshots if needed

**🚨 For Emergencies:**
• Billing issues: urgent@pnptv.app
• Access problems: support@pnptv.app
• Legal concerns: legal@pnptv.app

**⏱️ Response Time:**
• General inquiries: 24-48 hours
• Technical issues: 12-24 hours
• Emergencies: 2-6 hours

We're here to help! 🎬"""
        
        keyboard = [
            [InlineKeyboardButton("📧 Send Support Email", url="mailto:support@pnptv.app")],
            [InlineKeyboardButton("⚡ Urgent Support", url="mailto:urgent@pnptv.app")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=contact_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando contacto para {user_id}: {e}")
        await query.edit_message_text("❌ Error cargando información de contacto.")

async def show_help(query, user_id, data):
    """Sistema de ayuda completo"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        if lang == 'es':
            help_text = f"""🎬 **Centro de Ayuda PNP Television**

**🤖 Comandos Disponibles:**
• `/start` - Reiniciar el bot y seleccionar idioma
• `/help` - Mostrar esta ayuda
• `/plans` - Ver planes de suscripción
• `/status` - Verificar estado de suscripción

**💡 Preguntas Frecuentes:**

**🔐 ¿Cómo suscribirse?**
1. Usa /plans para ver opciones
2. Selecciona tu plan preferido
3. Completa el pago seguro via Bold.co
4. ¡Acceso instantáneo a tu contenido!

**📱 ¿Problemas de acceso?**
• Verifica que tengas suscripción activa
• Revisa los enlaces de invitación
• Contacta soporte si persiste

**💳 ¿Problemas de pago?**
• Todos los pagos via Bold.co (seguro)
• Soporte de tarjetas internacionales
• Confirmación instantánea

**🔄 ¿Cómo renovar?**
• Usa /plans antes del vencimiento
• La renovación extiende tu acceso actual
• Sin interrupciones en el servicio

**📧 ¿Necesitas más ayuda?**
¡Envía cualquier mensaje a este bot y nuestro equipo te contactará!

**🆔 Tu ID de usuario:** `{user_id}`
(Incluye este ID al contactar soporte)"""
        else:
            help_text = f"""🎬 **PNP Television Help Center**

**🤖 Available Commands:**
• `/start` - Restart bot and select language
• `/help` - Show this help
• `/plans` - View subscription plans
• `/status` - Check subscription status

**💡 Frequently Asked Questions:**

**🔐 How to Subscribe?**
1. Use /plans to see options
2. Choose your preferred plan
3. Complete secure payment via Bold.co
4. Get instant access to content!

**📱 Access Problems?**
• Verify you have active subscription
• Check invitation links in messages
• Contact support if issues persist

**💳 Payment Issues?**
• All payments via Bold.co (secure)
• International cards supported
• Instant confirmation

**🔄 How to Renew?**
• Use /plans before expiration
• Renewal extends your current access
• No service interruptions

**📧 Need More Help?**
Send any message to this bot and our team will contact you!

**🆔 Your User ID:** `{user_id}`
(Include this ID when contacting support)"""
        
        keyboard = [
            [InlineKeyboardButton("💎 View Plans", callback_data="show_plans")],
            [InlineKeyboardButton("📊 Check Status", callback_data="subscription_status")],
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text=help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando ayuda para {user_id}: {e}")
        await query.edit_message_text("❌ Error cargando centro de ayuda.")

# Funciones para el panel de administración

async def show_admin_menu(query, user_id, data):
    """Menú principal de administración"""
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized access")
        return
    
    try:
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        
        keyboard = [
            [InlineKeyboardButton("📊 Detailed Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Broadcast System", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📈 Metrics Dashboard", callback_data="admin_metrics")],
            [InlineKeyboardButton("🌐 Web Panel", url=f"http://{ADMIN_HOST}:{ADMIN_PORT}")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        
        text = f"""🔧 **Admin Control Panel**

**📊 Quick Overview:**
👥 Total Users: {stats['total']}
✅ Active Subscriptions: {stats['active']}
💰 Active Revenue: ${stats.get('active_revenue', 0):.2f}
📧 Total Revenue: ${stats.get('total_revenue', 0):.2f}

**🎯 Conversion Rate:** {(stats['active']/max(stats['total'], 1)*100):.1f}%

Select an option to continue:"""
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing admin menu: {e}")
        await query.edit_message_text("❌ Error accessing admin panel")

async def show_admin_stats(query, user_id, data):
    """Estadísticas detalladas para administradores"""
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized access")
        return
    
    try:
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        metrics = manager.get_metrics()

        # Construir breakdown por planes
        plan_text = ""
        for plan, data in stats.get('plans', {}).items():
            plan_text += f"• {plan}: {data['count']} users (${data['revenue']:.2f})\n"

        # Construir breakdown por idiomas
        lang_text = ""
        for lang, count in stats.get('languages', {}).items():
            flag = "🇺🇸" if lang == "en" else "🇪🇸" if lang == "es" else "🌍"
            percentage = (count / max(stats['total'], 1) * 100)
            lang_text += f"{flag} {lang.upper()}: {count} ({percentage:.1f}%)\n"

        text = f"""📊 **Comprehensive Statistics**

**👥 User Metrics:**
• Total Users: {stats['total']}
• Active Subscriptions: {stats['active']}
• Expired Subscriptions: {stats['churned']}
• Never Subscribed: {stats['never']}

**💰 Revenue Metrics:**
• Active MRR: ${stats.get('active_revenue', 0):.2f}
• Total Revenue: ${stats.get('total_revenue', 0):.2f}
• Conversion Rate: {(stats['active']/max(stats['total'], 1)*100):.1f}%

**📈 Performance:**
• Invites Sent: {metrics.get('invites_sent', 0)}
• Success Rate: {((metrics.get('invites_sent', 1) - metrics.get('invites_failed', 0)) / max(metrics.get('invites_sent', 1), 1) * 100):.1f}%
• Payments: {metrics.get('payments_processed', 0)}
• Reminders: {metrics.get('reminders_sent', 0)}

**🎯 Active Plans:**
{plan_text or 'No active subscriptions'}

**🌍 Languages:**
{lang_text or 'No users'}

**📅 Updated:** {datetime.now().strftime('%H:%M:%S')} UTC"""

        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("📊 Export Data", callback_data="admin_export")],
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu")]
        ]

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing admin stats: {e}")
        await query.edit_message_text("❌ Error retrieving statistics")

async def show_admin_users(query, user_id, data):
    """Panel de gestión de usuarios"""
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized access")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="admin_list_all")],
        [InlineKeyboardButton("✅ Active Subs", callback_data="admin_list_active")],
        [InlineKeyboardButton("⚠️ Expired Subs", callback_data="admin_list_churned")],
        [InlineKeyboardButton("❌ Never Subscribed", callback_data="admin_list_never")],
        [InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
        [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu")]
    ]
    
    text = """👥 **User Management Panel**

Select an option to manage users:

• **All Users** - View complete user list
• **Active Subs** - Users with active subscriptions
• **Expired Subs** - Users with expired subscriptions  
• **Never Subscribed** - Users who never purchased
• **Search User** - Find specific user by ID

Use the web panel for bulk operations and detailed management."""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_broadcast(query, user_id, data):
    """Panel de sistema de broadcast"""
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized access")
        return
    
    keyboard = [
        [InlineKeyboardButton("📢 Start Broadcast", callback_data="admin_new_broadcast")],
        [InlineKeyboardButton("📅 Scheduled Messages", callback_data="admin_scheduled")],
        [InlineKeyboardButton("📊 Broadcast Stats", callback_data="admin_broadcast_stats")],
        [InlineKeyboardButton("🎯 Test Message", callback_data="admin_test_broadcast")],
        [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu")]
    ]
    
    text = """📢 **Broadcast Management**

**Current Limits:**
• Max 12 broadcasts per 24 hours
• Scheduling up to 72 hours ahead
• Multi-language support
• User segmentation available

**Available Features:**
• Text messages with Markdown
• Photo broadcasts with captions
• Video broadcasts with captions
• GIF broadcasts with captions

**Targeting Options:**
• All users
• Active subscribers only
• Expired subscriptions
• Never purchased
• Language filtering (EN/ES)

Use `/broadcast` command for interactive wizard or select option below:"""
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_metrics(query, user_id, data):
    """Dashboard de métricas del sistema"""
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized access")
        return
    
    try:
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        metrics = manager.get_metrics()
        
        # Calcular métricas avanzadas
        total_users = stats['total']
        active_users = stats['active']
        
        conversion_rate = (active_users / max(total_users, 1)) * 100
        
        # Calcular ARPU (Average Revenue Per User)
        total_revenue = stats.get('total_revenue', 0)
        arpu = total_revenue / max(total_users, 1)
        
        # Tasa de éxito de invitaciones
        invites_sent = metrics.get('invites_sent', 0)
        invites_failed = metrics.get('invites_failed', 0)
        invite_success_rate = ((invites_sent - invites_failed) / max(invites_sent, 1)) * 100
        
        text = f"""📈 **Advanced Metrics Dashboard**

**📊 Key Performance Indicators:**
• Conversion Rate: {conversion_rate:.2f}%
• ARPU: ${arpu:.2f}
• Active Users: {active_users}/{total_users}
• Monthly Revenue: ${stats.get('active_revenue', 0):.2f}

**🎯 Operational Metrics:**
• Invite Success Rate: {invite_success_rate:.1f}%
• Invites Sent: {invites_sent}
• Failed Invites: {invites_failed}
• Payments Processed: {metrics.get('payments_processed', 0)}

**📧 Communication:**
• Reminders Sent: {metrics.get('reminders_sent', 0)}
• Support Requests: N/A
• Response Rate: N/A

**📅 Performance Trends:**
{self._format_recent_activity(stats.get('recent_activity', []))}

**🎯 Recommendations:**
{self._generate_recommendations(stats, metrics)}

Data updated in real-time."""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Metrics", callback_data="admin_metrics")],
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🌐 Web Dashboard", url=f"http://{ADMIN_HOST}:{ADMIN_PORT}")],
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu")]
        ]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing admin metrics: {e}")
        await query.edit_message_text("❌ Error loading metrics dashboard")

def _format_recent_activity(activity_data):
    """Formatear datos de actividad reciente"""
    if not activity_data:
        return "• No recent activity data available"
    
    result = ""
    for entry in activity_data[:3]:  # Últimos 3 días
        date = entry.get('date', 'Unknown')
        new_users = entry.get('new_users', 0)
        result += f"• {date}: {new_users} new users\n"
    
    return result.rstrip('\n') or "• No recent activity"

def _generate_recommendations(stats, metrics):
    """Generar recomendaciones basadas en métricas"""
    recommendations = []
    
    # Analizar tasa de conversión
    conversion_rate = (stats['active'] / max(stats['total'], 1)) * 100
    if conversion_rate < 10:
        recommendations.append("Low conversion rate - consider promotional campaigns")
    elif conversion_rate > 30:
        recommendations.append("Excellent conversion rate - scale marketing efforts")
    
    # Analizar usuarios que nunca compraron
    never_bought = stats.get('never', 0)
    if never_bought > stats['active']:
        recommendations.append("Many users haven't purchased - send targeted offers")
    
    # Analizar tasa de éxito de invitaciones
    invite_success = ((metrics.get('invites_sent', 1) - metrics.get('invites_failed', 0)) / max(metrics.get('invites_sent', 1), 1)) * 100
    if invite_success < 90:
        recommendations.append("Check channel permissions and bot admin status")
    
    return "\n".join(f"• {rec}" for rec in recommendations[:3]) or "• All metrics looking good!"

# Import adicional para datetime
from datetime import datetime# -*- coding: utf-8 -*-
"""
CALLBACKS MEJORADOS CON MANEJO DE ERRORES Y VALIDACIONES
=======================================================
Sistema completo con persistencia de estado y manejo robusto de errores
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging
from datetime import datetime
from bot.texts import TEXTS
from bot.config import PLANS, ADMIN_IDS, CHANNELS
from bot.enhanced_subscriber_manager import get_subscriber_manager  # ✅ CORREGIDO: Import correcto

logger = logging.getLogger(__name__)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler principal de callbacks con manejo robusto de errores"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        logger.info(f"Callback received: {data} from user {user_id}")
        
        # Router completo de callbacks con validación
        callback_handlers = {
            "lang_": handle_language_selection,
            "confirm_age": handle_age_confirmation,
            "decline_age": handle_age_decline,
            "accept_terms": handle_terms_acceptance,
            "decline_terms": handle_terms_decline,
            "main_menu": show_main_menu,
            "show_plans": show_plans,
            "policies": show_policies,
            "terms": show_terms,
            "privacy": show_privacy,
            "refund": show_refund,
            "contact": show_contact,
            "help": show_help,
            "admin_stats": show_admin_stats,
            "admin_menu": show_admin_menu,
            "admin_users": show_admin_users,
            "admin_broadcast": show_admin_broadcast,
            "admin_metrics": show_admin_metrics,
            "plan_": handle_plan_selection,
            "subscription_status": show_subscription_status,
        }
        
        # Buscar handler apropiado
        handler_found = False
        for prefix, handler in callback_handlers.items():
            if data.startswith(prefix) or data == prefix.rstrip("_"):
                await handler(query, user_id, data)
                handler_found = True
                break
        
        if not handler_found:
            logger.warning(f"Callback desconocido: {data} de usuario {user_id}")
            await query.edit_message_text(
                "❌ Esta función no está disponible temporalmente.\n"
                "Usa /start para volver al menú principal."
            )
            
    except TelegramError as e:
        logger.error(f"Error de Telegram en callback {query.data}: {e}")
        try:
            await query.edit_message_text(
                "❌ Error de conexión. Por favor intenta de nuevo.\n"
                "Si el problema persiste, usa /start"
            )
        except:
            # Si no puede editar el mensaje, enviar uno nuevo
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="❌ Error de conexión. Usa /start para continuar."
            )
    except Exception as e:
        logger.error(f"Error crítico en callback {query.data}: {e}")
        try:
            await query.edit_message_text(
                "❌ Error interno del sistema.\n"
                "El equipo técnico ha sido notificado.\nUsa /start para continuar."
            )
        except:
            pass

async def handle_language_selection(query, user_id, data):
    """Selección de idioma con validación mejorada"""
    try:
        lang = data.split("_")[1]
        
        # Validar idioma
        if lang not in ['en', 'es']:
            logger.warning(f"Idioma inválido seleccionado: {lang}")
            await query.edit_message_text("❌ Idioma no válido. Usa /start para reiniciar.")
            return

        manager = await get_subscriber_manager()
        await manager.record_user(
            user_id, 
            language=lang,
            username=query.from_user.username,
            first_name=query.from_user.first_name,
            last_name=query.from_user.last_name
        )
        
        logger.info(f"Usuario {user_id} seleccionó idioma: {lang}")
        await show_age_verification(query, user_id, lang)
        
    except Exception as e:
        logger.error(f"Error en selección de idioma para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error guardando preferencia de idioma.\n"
            "Por favor intenta de nuevo con /start"
        )

async def show_age_verification(query, user_id, lang=None):
    """Verificación de edad con recuperación de estado"""
    if not lang:
        try:
            manager = await get_subscriber_manager()
            user_status = await manager.get_user_status(user_id)
            lang = user_status.get('language', 'en')
        except Exception as e:
            logger.error(f"Error obteniendo idioma para {user_id}: {e}")
            lang = 'en'
    
    keyboard = [
        [InlineKeyboardButton(TEXTS[lang]["confirm_age"], callback_data="confirm_age")],
        [InlineKeyboardButton(TEXTS[lang]["decline_age"], callback_data="decline_age")]
    ]
    
    try:
        await query.edit_message_text(
            text=TEXTS[lang]["age_warning"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except TelegramError as e:
        logger.error(f"Error mostrando verificación de edad: {e}")
        await query.edit_message_text("❌ Error en el sistema. Usa /start para reiniciar.")

async def handle_age_confirmation(query, user_id, data):
    """Confirmación de edad con persistencia mejorada"""
    try:
        manager = await get_subscriber_manager()
        await manager.record_user(user_id, age_verified=True)
        
        # Log de actividad de seguridad
        logger.info(f"Usuario {user_id} confirmó verificación de edad - IP: {query.from_user.id}")
        
        await show_terms_acceptance(query, user_id)
        
    except Exception as e:
        logger.error(f"Error guardando verificación de edad para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error en verificación. Por favor contacta soporte si persiste."
        )

async def handle_age_decline(query, user_id, data):
    """Manejar rechazo de edad con mensaje bilingüe"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        if lang == 'es':
            message = "❌ Debes tener 18+ años para usar este servicio.\n\n" \
                     "Este contenido está restringido a adultos mayores de edad."
        else:
            message = "❌ You must be 18+ to use this service.\n\n" \
                     "This content is restricted to adults only."
        
        await query.edit_message_text(message)
        
    except Exception as e:
        logger.error(f"Error en rechazo de edad: {e}")
        await query.edit_message_text(
            "❌ You must be 18+ to use this service.\n"
            "❌ Debes tener 18+ para usar este servicio."
        )

async def show_terms_acceptance(query, user_id):
    """Mostrar términos con formato mejorado"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        terms_text = TEXTS[lang]["terms_content"]
        
        # Agregar texto de aceptación con formato
        if lang == 'es':
            acceptance_text = "\n\n⚠️ **IMPORTANTE:** Al continuar, aceptas nuestros términos y condiciones.\n\n" \
                            "**✅ Acepto** - Continuar con el registro\n" \
                            "**❌ No acepto** - Salir del servicio"
            accept_button = "✅ Acepto los términos"
            decline_button = "❌ No acepto"
        else:
            acceptance_text = "\n\n⚠️ **IMPORTANT:** By continuing, you accept our terms and conditions.\n\n" \
                            "**✅ Accept** - Continue with registration\n" \
                            "**❌ Decline** - Exit service"
            accept_button = "✅ I accept the terms"
            decline_button = "❌ I don't accept"
        
        keyboard = [
            [InlineKeyboardButton(accept_button, callback_data="accept_terms")],
            [InlineKeyboardButton(decline_button, callback_data="decline_terms")]
        ]
        
        # Truncar términos si son muy largos para Telegram
        full_text = terms_text + acceptance_text
        if len(full_text) > 4096:
            terms_text = terms_text[:3500] + "\n\n[...términos completos disponibles en el menú principal...]"
            full_text = terms_text + acceptance_text
        
        await query.edit_message_text(
            text=full_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando términos para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error cargando términos y condiciones.\n"
            "Por favor contacta soporte."
        )

async def handle_terms_acceptance(query, user_id, data):
    """Manejar aceptación de términos con timestamp"""
    try:
        manager = await get_subscriber_manager()
        await manager.record_user(user_id, terms_accepted=True)
        
        # Log de aceptación legal
        logger.info(f"Usuario {user_id} aceptó términos y condiciones - Timestamp: {datetime.now()}")
        
        await show_main_menu(query, user_id)
        
    except Exception as e:
        logger.error(f"Error guardando aceptación de términos para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error procesando aceptación.\n"
            "Por favor intenta de nuevo o contacta soporte."
        )

async def handle_terms_decline(query, user_id, data):
    """Manejar rechazo de términos"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        if lang == 'es':
            message = "❌ Debes aceptar los términos y condiciones para usar este servicio.\n\n" \
                     "Si tienes preguntas sobre nuestros términos, contacta: support@pnptv.app"
        else:
            message = "❌ You must accept the terms and conditions to use this service.\n\n" \
                     "If you have questions about our terms, contact: support@pnptv.app"
        
        await query.edit_message_text(message)
        
    except Exception as e:
        logger.error(f"Error en rechazo de términos: {e}")
        await query.edit_message_text(
            "❌ You must accept the terms and conditions to use this service.\n"
            "❌ Debes aceptar los términos y condiciones para usar este servicio."
        )

async def show_main_menu(query, user_id, data=None):
    """Menú principal con verificación completa de estado"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        
        # Verificar progreso de verificación
        if not user_status.get('age_verified', False):
            await show_age_verification(query, user_id, user_status.get('language', 'en'))
            return
        
        if not user_status.get('terms_accepted', False):
            await show_terms_acceptance(query, user_id)
            return
        
        lang = user_status.get('language', 'en')
        
        # Crear menú contextual basado en estado de suscripción
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["plans"], callback_data="show_plans")],
            [InlineKeyboardButton("📊 My Subscription", callback_data="subscription_status")]
        ]
        
        # Agregar botones adicionales
        keyboard.extend([
            [InlineKeyboardButton(TEXTS[lang]["policies_menu"], callback_data="policies")],
            [InlineKeyboardButton(TEXTS[lang]["contact"], callback_data="contact")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        
        # Botón admin si es administrador
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_menu")])
        
        # Personalizar mensaje de bienvenida basado en estado
        subscription_status = user_status.get('status', 'never')
        if subscription_status == 'active':
            welcome_extra = "\n\n✅ You have an active subscription!"
        elif subscription_status == 'churned':
            welcome_extra = "\n\n⚠️ Your subscription has expired. Renew to regain access!"
        else:
            welcome_extra = "\n\n💎 Ready to subscribe? Check our plans below!"
        
        text = f"{TEXTS[lang]['welcome']}\n\n{TEXTS[lang]['welcome_desc']}{welcome_extra}"
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando menú principal para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error cargando menú principal.\n"
            "Usa /start para reiniciar o contacta soporte."
        )

async def show_plans(query, user_id, data):
    """Mostrar planes con información detallada y precios actualizados"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        keyboard = []
        
        # Ordenar planes por duración para mejor presentación
        sorted_plans = sorted(
            PLANS.items(), 
            key=lambda x: x[1]['duration_days']
        )
        
        for plan_id, plan_info in sorted_plans:
            channels_count = len(plan_info.get('channels', []))
            
            # Crear texto descriptivo del plan
            if plan_info['duration_days'] >= 365:
                duration_text = f"{plan_info['duration_days']//365} year(s)"
            elif plan_info['duration_days'] >= 30:
                duration_text = f"{plan_info['duration_days']//30} month(s)"
            else:
                duration_text = f"{plan_info['duration_days']} days"
            
            plan_text = f"{plan_info['name']} - {plan_info['price']}\n" \
                       f"📺 {channels_count} channels • ⏱️ {duration_text}"
            
            keyboard.append([
                InlineKeyboardButton(plan_text, callback_data=f"plan_{plan_id}")
            ])
        
        keyboard.append([InlineKeyboardButton(TEXTS[lang]["back"], callback_data="main_menu")])
        
        # Texto mejorado con beneficios
        benefits_text = TEXTS[lang]['plan_benefits']
        text = f"""{TEXTS[lang]['plans_title']}

{benefits_text}

💡 **All plans include:**
• Instant access after payment
• High-quality exclusive content  
• 24/7 customer support
• Secure payment via Bold.co

Choose your perfect plan below:"""
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando planes para {user_id}: {e}")
        await query.edit_message_text(
            "❌ Error cargando planes de suscripción.\n"
            "Por favor intenta de nuevo."
        )

async def handle_plan_selection(query, user_id, data):
    """Selección de plan con información completa y seguridad mejorada"""
    try:
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(user_id)
        lang = user_status.get('language', 'en')
        
        plan_id = data.replace("plan_", "")
        
        if plan_id not in PLANS:
            logger.warning(f"Plan inválido seleccionado: {plan_id} por usuario {user_id}")
            await query.edit_message_text("❌ Plan no válido. Por favor selecciona otro plan.")
            return
        
        plan_info = PLANS[plan_id]
        
        # Verificar si el usuario ya tiene suscripción activa
        current_status = user_status.get('status', 'never')
        if current_status == 'active':
            subscription = user_status.get('subscription')
            current_plan = subscription.get('plan') if subscription else 'Unknown'
            expires_at = subscription.get('expires_at') if subscription else None
            
            warning_text = f"\n\n⚠️ **Note:** You currently have an active subscription ({current_plan})"
            if expires_at:
                warning_text += f" until {expires_at.strftime('%Y-%m-%d')}"
            warning_text += ".\nThis new subscription will extend your current access."
        else:
            warning_text = ""
        
        # Descripción en el idioma correcto
        from bot.config import PLAN_DESCRIPTIONS
        description = PLAN_DESCRIPTIONS.get(lang, PLAN_DESCRIPTIONS["en"])
        
        # Información de canales con nombres descriptivos
        channels = plan_info.get('channels', [])
        channels_text = f"📺 **Channels included:** {len(channels)}\n"
        for i, channel_name in enumerate(channels, 1):
            channels_text += f"• Premium Channel {i}\n"
        
        # Generar enlace de pago seguro
        from bot.config import generate_bold_link
        try:
            payment_url = generate_bold_link(
                plan_info["link_id"], 
                user_id, 
                plan_id
            )
        except Exception as e:
            logger.error(f"Error generando enlace de pago: {e}")
            await query.edit_message_text(
                "❌ Error generando enlace de pago.\n"
                "Por favor contacta soporte."
            )
            return
        
        # Calcular valor por día
        daily_cost = float(plan_info['price'].replace('$', '')) / plan_info['duration_days']
        
        text = f"""💎 **{plan_info['name']}**

💰 **Price:** {plan_info['price']} USD
⏱️ **Duration:** {plan_info['duration_days']} days
📊 **Value:** ${daily_cost:.2f} per day

{channels_text}

**🎬 What you get:**
{description}

{warning_text}

🔐 **Secure Payment Information:**
• Payment processed by Bold.co (secure & trusted)
• Instant access after confirmation
• User ID: `{user_id}` (for support reference)
• Plan ID: `{plan_id}`

Click below to complete your secure payment:"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Pay Securely with Bold.co", url=payment_url)],
            [InlineKeyboardButton("🔄 Choose Different Plan", callback_data="show_plans")