# -*- coding: utf-8 -*-
import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager with validation"""
    
    def __init__(self):
        self.validate_required_vars()
        self._setup_logging()
    
    def validate_required_vars(self):
        """Validate that all required environment variables are set"""
        # Core required variables
        required_vars = {
            'BOT_TOKEN': 'Telegram bot token',
            'DATABASE_URL': 'PostgreSQL database URL',
            'BOLD_IDENTITY_KEY': 'Bold.co payment identity key'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                # Allow dummy values for testing
                if "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv):
                    continue
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            error_msg = f"Missing required environment variables:\n" + "\n".join(f"- {var}" for var in missing_vars)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✅ All required environment variables validated")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

# Initialize config
config = Config()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN and "pytest" not in sys.modules:
    BOT_TOKEN = "TEST_TOKEN" if any("pytest" in arg for arg in sys.argv) else None

# Parse ADMIN_IDS with better error handling
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if admin_ids_str:
    try:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
        logger.info(f"✅ Admin IDs configured: {len(ADMIN_IDS)} admins")
    except ValueError as e:
        logger.warning(f"Warning: Error parsing ADMIN_IDS: {e}")

# Payment settings
BOLD_IDENTITY_KEY = os.getenv("BOLD_IDENTITY_KEY")
BOLD_WEBHOOK_SECRET = os.getenv("BOLD_WEBHOOK_SECRET")

if not BOLD_WEBHOOK_SECRET:
    logger.warning("⚠️ BOLD_WEBHOOK_SECRET not set - webhook signature verification will be skipped")

# Customer service settings
CUSTOMER_SERVICE_CHAT_ID = os.getenv("CUSTOMER_SERVICE_CHAT_ID")
if CUSTOMER_SERVICE_CHAT_ID:
    try:
        CUSTOMER_SERVICE_CHAT_ID = int(CUSTOMER_SERVICE_CHAT_ID)
        logger.info("✅ Customer service chat ID configured")
    except ValueError:
        logger.warning(f"Warning: CUSTOMER_SERVICE_CHAT_ID must be a valid integer")
        CUSTOMER_SERVICE_CHAT_ID = None

# Plan configuration
PLAN_LINK_IDS = {
    "Trial Trip": "LNK_O7C5LTPYFP",
    "Cloudy Month": "LNK_52ZQ7A0I9I",
    "Frequent Flyer": "LNK_468D3W49LB",
    "Slam Surfer": "LNK_EMVGMPYMGJ",
    "Full Year": "LNK_253P067SB1",
    "PNP Forever": "LNK_PNM53KLD99"
}

def generate_bold_link(link_id: str, user_id: int, plan_id: str) -> str:
    """Generate a Bold.co payment URL including the plan identifier."""
    if not BOLD_IDENTITY_KEY:
        raise ValueError("BOLD_IDENTITY_KEY not configured")
    
    return (
        f"https://checkout.bold.co/payment/{link_id}"
        f"?identity_key={BOLD_IDENTITY_KEY}"
        f"&metadata[user_id]={user_id}"
        f"&metadata[plan_id]={plan_id}"
    )

# Channel settings - Global channel registry
CHANNELS = {
    "channel_1": -1002068120499,
    "channel_2": -1001234567890,
    "channel_3": -1001234567891,
    "channel_4": -1001234567892,
    "channel_5": -1001234567893,
}

ALL_CHANNEL_IDS = list(CHANNELS.values())

# Plan configurations with multilingual descriptions
PLAN_DESCRIPTIONS = {
    "en": "Access to **exclusive channels** featuring explicit PNP videos – **Latino men smoking and slamming**.\n• **200+ clips**, each averaging around **10 minutes** of intense action.\n• **Invitation to our virtual slam & smoke parties** – join the vibe, live and uncensored.\n• **Bonus:** Early access to our **upcoming web app** – launching soon!",
    "es": "Acceso a **canales exclusivos** con videos explícitos PNP – **Hombres latinos fumando y slamming**.\n• **200+ clips**, cada uno promedio de **10 minutos** de acción intensa.\n• **Invitación a nuestras fiestas virtuales de slam & smoke** – únete al ambiente, en vivo y sin censura.\n• **Bonus:** Acceso anticipado a nuestra **próxima aplicación web** – ¡próximamente!"
}

# Enhanced PLANS with channel assignments
PLANS = {
    "trial": {
        "name": "Trial Trip",
        "price": "$14.99",
        "duration_days": 7,
        "link_id": "LNK_O7C5LTPYFP",
        "channels": ["channel_1"]
    },
    "monthly": {
        "name": "Cloudy Month",
        "price": "$24.99",
        "duration_days": 30,
        "link_id": "LNK_52ZQ7A0I9I",
        "channels": ["channel_1", "channel_2"]
    },
    "vip": {
        "name": "Frequent Flyer",
        "price": "$49.99",
        "duration_days": 90,
        "link_id": "LNK_468D3W49LB",
        "channels": ["channel_1", "channel_2", "channel_3"]
    },
    "halfyear": {
        "name": "Slam Surfer",
        "price": "$79.99",
        "duration_days": 180,
        "link_id": "LNK_EMVGMPYMGJ",
        "channels": ["channel_1", "channel_2", "channel_3", "channel_4"]
    },
    "yearly": {
        "name": "Full Year",
        "price": "$99.99",
        "duration_days": 365,
        "link_id": "LNK_253P067SB1",
        "channels": ["channel_1", "channel_2", "channel_3", "channel_4", "channel_5"]
    },
    "lifetime": {
        "name": "PNP Forever",
        "price": "$249.99",
        "duration_days": 3650,
        "link_id": "LNK_PNM53KLD99",
        "channels": ["channel_1", "channel_2", "channel_3", "channel_4", "channel_5"]
    }
}

def get_plan_channels(plan_name: str) -> List[int]:
    """Get the list of channel IDs for a specific plan."""
    for plan_id, plan_info in PLANS.items():
        if plan_info["name"] == plan_name:
            channel_names = plan_info.get("channels", [])
            return [CHANNELS[name] for name in channel_names if name in CHANNELS]
    return []

def get_plan_channel_names(plan_name: str) -> List[str]:
    """Get the list of channel names for a specific plan."""
    for plan_id, plan_info in PLANS.items():
        if plan_info["name"] == plan_name:
            return plan_info.get("channels", [])
    return []

# Admin panel settings
ADMIN_PORT = int(os.getenv("ADMIN_PORT", 8080))
ADMIN_HOST = os.getenv("ADMIN_HOST", "0.0.0.0")

# Database settings with improved configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    if "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv):
        DATABASE_URL = "postgresql://test:test@localhost:5432/test_pnp_bot"
    else:
        DATABASE_URL = "postgresql://user:password@localhost:5432/pnp_bot"
        logger.warning("⚠️ DATABASE_URL not set, using default development URL")

# Enhanced database pool settings
DATABASE_CONFIG = {
    "min_size": int(os.getenv("DB_MIN_POOL_SIZE", 5)),
    "max_size": int(os.getenv("DB_MAX_POOL_SIZE", 20)),
    "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", 60))
}

# Webhook settings for Railway deployment
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("PORT", 8000))

if not WEBHOOK_URL:
    logger.warning("⚠️ WEBHOOK_URL not set - webhook may not function properly in production")

# Reminder settings
REMINDER_DAYS_BEFORE_EXPIRY = int(os.getenv("REMINDER_DAYS_BEFORE_EXPIRY", 3))

# Rate limiting settings
RATE_LIMIT_CONFIG = {
    "invite_delay": float(os.getenv("INVITE_DELAY", 0.1)),  # Reduced from 0.5
    "broadcast_delay": float(os.getenv("BROADCAST_DELAY", 0.05)),
    "max_retries": int(os.getenv("MAX_RETRIES", 3))
}

# Security settings
SECURITY_CONFIG = {
    "require_webhook_signature": os.getenv("REQUIRE_WEBHOOK_SIGNATURE", "false").lower() == "true",
    "log_sensitive_data": os.getenv("LOG_SENSITIVE_DATA", "false").lower() == "true",
    "max_broadcast_per_day": int(os.getenv("MAX_BROADCAST_PER_DAY", 12))
}

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

logger.info(f"🚀 Configuration loaded for environment: {ENVIRONMENT}")
logger.info(f"📊 Database pool: {DATABASE_CONFIG['min_size']}-{DATABASE_CONFIG['max_size']} connections")
logger.info(f"🔒 Security: Webhook signature {'required' if SECURITY_CONFIG['require_webhook_signature'] else 'optional'}")
