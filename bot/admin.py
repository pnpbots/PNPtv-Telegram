# -*- coding: utf-8 -*-
"""Admin command handlers with enhanced functionality."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.texts import TEXTS
from bot.config import ADMIN_IDS, ADMIN_HOST, ADMIN_PORT
from bot.enhanced_subscriber_manager import get_subscriber_manager  # ✅ CORREGIDO: Import correcto

logger = logging.getLogger(__name__)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command with enhanced admin panel."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        # ✅ CORREGIDO: Obtener manager instance de forma asíncrona
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        metrics = manager.get_metrics()
        
        keyboard = [
            [InlineKeyboardButton("📊 Detailed Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Broadcast Center", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🌐 Web Panel", url=f"http://{ADMIN_HOST}:{ADMIN_PORT}")],
            [InlineKeyboardButton("📈 Metrics Dashboard", callback_data="admin_metrics")]
        ]
        
        text = f"""🔧 **Enhanced Admin Panel**

**📊 Quick Stats:**
👥 Total users: {stats['total']}
✅ Active subscriptions: {stats['active']}
💰 Active revenue: ${stats['active_revenue']:.2f}
📧 Reminders sent today: {metrics.get('reminders_sent', 0)}

**🌐 Web Panel:** http://{ADMIN_HOST}:{ADMIN_PORT}

Choose an option below or use the web panel for advanced management."""
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        await update.message.reply_text("❌ Error accessing admin panel. Check logs for details.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command with comprehensive statistics."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        # ✅ CORREGIDO: Obtener manager instance de forma asíncrona
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        metrics = manager.get_metrics()
        
        # Calcular tasas de conversión
        conversion_rate = (stats['active'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        # Formatear estadísticas por plan
        plan_breakdown = ""
        for plan, data in stats.get('plans', {}).items():
            plan_breakdown += f"  • {plan}: {data['count']} users (${data['revenue']:.2f})\n"
        
        # Formatear estadísticas por idioma
        lang_breakdown = ""
        for lang, count in stats.get('languages', {}).items():
            flag = "🇺🇸" if lang == "en" else "🇪🇸" if lang == "es" else "🌍"
            percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            lang_breakdown += f"  {flag} {lang.upper()}: {count} ({percentage:.1f}%)\n"
        
        text = f"""📊 **Comprehensive Bot Statistics**

**👥 User Overview:**
• Total users: {stats['total']}
• Active subscriptions: {stats['active']} ({conversion_rate:.1f}% conversion)
• Expired subscriptions: {stats['churned']}
• Never subscribed: {stats['never']}

**💰 Revenue:**
• Active revenue: ${stats['active_revenue']:.2f}
• Total revenue: ${stats['total_revenue']:.2f}

**📈 Performance Metrics:**
• Invites sent: {metrics.get('invites_sent', 0)}
• Invites failed: {metrics.get('invites_failed', 0)}
• Payments processed: {metrics.get('payments_processed', 0)}
• Reminders sent: {metrics.get('reminders_sent', 0)}

**🎯 Active Plans:**
{plan_breakdown or "  No active subscriptions"}

**🌍 Language Distribution:**
{lang_breakdown or "  No users registered"}

**📅 Last updated:** just now

🌐 **Web Panel:** http://{ADMIN_HOST}:{ADMIN_PORT}"""

        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("📊 Export Data", callback_data="admin_export")],
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu")]
        ]
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Error retrieving statistics. Check system status.")

async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin_help command with comprehensive command list."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        text = f"""🔧 **Enhanced Admin Commands Reference**

**📊 Statistics & Monitoring:**
/admin - Main admin panel with quick stats
/stats - Comprehensive bot statistics
/metrics - Performance metrics dashboard

**👥 User Management:**
/reply [user_id] [message] - Reply to customer inquiry
/broadcast - Interactive broadcast system
/user_info [user_id] - Get detailed user information
/ban_user [user_id] - Temporarily ban user

**💰 Subscription Management:**
/manual_add [user_id] [plan] - Manually add subscription
/extend_sub [user_id] [days] - Extend existing subscription
/revoke_access [user_id] - Manually revoke channel access

**🔧 System Management:**
/system_health - Check system health status
/cleanup_logs - Clean old activity logs
/test_channels - Test bot access to all channels

**📢 Broadcasting:**
/broadcast - Start interactive broadcast wizard
/scheduled_broadcasts - View scheduled messages
/broadcast_stats - Broadcasting performance metrics

**🌐 Advanced Features:**
• **Web Panel:** http://{ADMIN_HOST}:{ADMIN_PORT}
• **API Endpoints:** /api/stats, /api/users, /api/subscribers
• **Health Check:** /health
• **Payment Webhook:** /webhook/payment

**📋 Quick Tips:**
• Use the web panel for bulk operations
• Check /system_health regularly
• Monitor conversion rates in /stats
• Use /broadcast for important announcements

**🆘 Emergency Commands:**
/emergency_stop - Stop all automated processes
/backup_db - Create database backup
/restore_service - Restart critical services

For detailed documentation, visit the web panel or check the README file."""
        
        keyboard = [
            [InlineKeyboardButton("🌐 Open Web Panel", url=f"http://{ADMIN_HOST}:{ADMIN_PORT}")],
            [InlineKeyboardButton("📊 View Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Admin Menu", callback_data="admin_menu")]
        ]
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_help_command: {e}")
        await update.message.reply_text("❌ Error retrieving help information")

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get detailed information about a specific user."""
    try:
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(TEXTS["en"]["admin_only"])
            return
        
        if not context.args:
            await update.message.reply_text(
                "📝 **Usage:** `/user_info [user_id]`\n\n"
                "**Example:** `/user_info 123456789`",
                parse_mode="Markdown"
            )
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
            return
        
        manager = await get_subscriber_manager()
        user_status = await manager.get_user_status(target_user_id)
        
        if not user_status:
            await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
            return
        
        # Format user information
        status_emoji = {
            'active': '✅',
            'churned': '⚠️', 
            'never': '❌'
        }.get(user_status['status'], '❓')
        
        subscription_info = ""
        if user_status['subscription']:
            sub = user_status['subscription']
            subscription_info = f"""
**💎 Subscription Details:**
• Plan: {sub['plan']}
• Started: {sub['start_date'].strftime('%Y-%m-%d %H:%M')} UTC
• Expires: {sub['expires_at'].strftime('%Y-%m-%d %H:%M')} UTC
• Amount: ${sub['payment_amount']:.2f} USD
• Transaction: {sub['transaction_id'] or 'N/A'}"""
        
        channel_info = ""
        active_channels = [ch for ch in user_status['channel_access'] if ch['revoked_at'] is None]
        if active_channels:
            channel_info = f"\n**📺 Active Channels:** {len(active_channels)}"
            for ch in active_