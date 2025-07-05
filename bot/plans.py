# -*- coding: utf-8 -*-
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from bot.config import PLANS

logger = logging.getLogger(__name__)

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /plans command"""
    try:
        user_id = update.effective_user.id
        
        keyboard = []
        
        for plan_id, plan_info in PLANS.items():
            plan_text = f"{plan_info['name']} - {plan_info['price']}"
            keyboard.append([
                InlineKeyboardButton(plan_text, callback_data=f"plan_{plan_id}")
            ])
        
        text = """🎬 **Choose Your Plan**

Select the perfect plan for your needs and get instant access to premium content.

Choose your perfect plan below:"""
        
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in plans_command: {e}")
        await update.message.reply_text("❌ Error showing plans")