#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PNP Television Bot - Enhanced Production Entry Point
=================================================
Optimized for Railway deployment with comprehensive error handling and monitoring
"""

import asyncio
import logging
import os
import sys
import signal
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def setup_logging():
    """Configure enhanced production logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Configure logging format based on environment
    if environment == "production":
        log_format = '%(asctime)s [%(process)d] [%(levelname)s] %(name)s: %(message)s'
    else:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels for noisy libraries
    library_log_levels = {
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "telegram": logging.INFO,
        "asyncpg": logging.WARNING,
        "uvicorn": logging.INFO,
        "fastapi": logging.INFO
    }
    
    for library, level in library_log_levels.items():
        logging.getLogger(library).setLevel(level)
    
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Logging configured at {log_level} level for {environment}")
    return logger

def validate_environment():
    """Validate critical environment variables and configuration"""
    logger = logging.getLogger(__name__)
    
    # Critical environment variables
    critical_vars = {
        'BOT_TOKEN': 'Telegram bot token',
        'DATABASE_URL': 'PostgreSQL database connection string',
        'BOLD_IDENTITY_KEY': 'Bold.co payment identity key'
    }
    
    missing_vars = []
    for var, description in critical_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.error("❌ Missing critical environment variables:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        logger.error("Please check your .env file or Railway environment variables")
        return False
    
    # Validate optional but recommended variables
    optional_vars = {
        'ADMIN_IDS': 'Administrator user IDs',
        'BOLD_WEBHOOK_SECRET': 'Webhook signature verification',
        'CUSTOMER_SERVICE_CHAT_ID': 'Support chat configuration'
    }
    
    missing_optional = []
    for var, description in optional_vars.items():
        if not os.getenv(var):
            missing_optional.append(f"{var} ({description})")
    
    if missing_optional:
        logger.warning("⚠️ Missing optional environment variables:")
        for var in missing_optional:
            logger.warning(f"   - {var}")
        logger.warning("Some features may be limited")
    
    logger.info("✅ Environment validation completed")
    return True

async def initialize_database():
    """Initialize database connection and schema"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 Initializing database connection...")
        from bot.enhanced_subscriber_manager import get_subscriber_manager
        
        manager = await get_subscriber_manager()
        stats = await manager.get_stats()
        
        logger.info(f"✅ Database initialized successfully")
        logger.info(f"📊 Current stats: {stats['total']} users, {stats['active']} active subscriptions")
        
        return manager
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

async def test_bot_connection():
    """Test Telegram bot API connection"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 Testing Telegram bot connection...")
        from telegram import Bot
        from bot.config import BOT_TOKEN
        
        bot = Bot(token=BOT_TOKEN)
        bot_info = await bot.get_me()
        
        logger.info(f"✅ Bot connected successfully")
        logger.info(f"🤖 Bot info: @{bot_info.username} (ID: {bot_info.id})")
        
        return bot_info
        
    except Exception as e:
        logger.error(f"❌ Bot connection failed: {e}")
        raise

async def start_automation_services():
    """Start background automation services"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 Starting automation services...")
        
        # Import automation services
        from bot.start import start_automation_tasks
        
        # Start background tasks
        await start_automation_tasks()
        
        logger.info("✅ Automation services started successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to start automation services: {e}")
        # Don't raise - automation is not critical for basic bot operation
        logger.warning("⚠️ Bot will continue without automation services")

class GracefulShutdown:
    """Handle graceful shutdown of services"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self._shutdown())
    
    async def _shutdown(self):
        """Perform graceful shutdown"""
        self.logger.info("🔄 Starting graceful shutdown...")
        
        try:
            # Cleanup database connections
            from bot.enhanced_subscriber_manager import cleanup_subscriber_manager
            await cleanup_subscriber_manager()
            
            # Set shutdown event
            self.shutdown_event.set()
            
            self.logger.info("✅ Graceful shutdown completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
            self.shutdown_event.set()

async def main():
    """Enhanced main entry point with comprehensive initialization"""
    logger = setup_logging()
    
    # Setup graceful shutdown
    shutdown_handler = GracefulShutdown()
    shutdown_handler.setup_signal_handlers()
    
    try:
        logger.info("🚀 Starting PNP Television Bot Ultimate...")
        logger.info(f"📁 Project root: {project_root}")
        logger.info(f"🐍 Python version: {sys.version}")
        logger.info(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
        logger.info(f"🚀 Platform: {sys.platform}")
        
        # Validate environment
        if not validate_environment():
            sys.exit(1)
        
        # Initialize core services
        logger.info("🔄 Initializing core services...")
        
        # Test database connection
        manager = await initialize_database()
        
        # Test bot connection
        bot_info = await test_bot_connection()
        
        # Import and setup bot application
        logger.info("🔄 Initializing bot application...")
        from bot.start import main as bot_main
        
        # Start automation services (non-blocking)
        await start_automation_services()
        
        logger.info("✅ All services initialized successfully")
        logger.info("🤖 Bot is starting up...")
        
        # Start the bot (this will run until shutdown)
        bot_task = asyncio.create_task(bot_main())
        shutdown_task = asyncio.create_task(shutdown_handler.shutdown_event.wait())
        
        # Wait for either bot completion or shutdown signal
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if bot task completed with an error
        if bot_task in done:
            result = bot_task.result()  # This will raise if there was an exception
        
        logger.info("🛑 Bot stopped")
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        
        # Try to send error notification to admins
        try:
            from bot.config import ADMIN_IDS
            from telegram import Bot
            
            if ADMIN_IDS and os.getenv('BOT_TOKEN'):
                error_bot = Bot(token=os.getenv('BOT_TOKEN'))
                error_message = f"""🚨 **Bot Crashed**

❌ **Fatal Error:** {str(e)[:200]}
⏰ **Time:** {asyncio.get_event_loop().time()}
🌍 **Environment:** {os.getenv('ENVIRONMENT', 'unknown')}

The bot has stopped and requires manual intervention."""
                
                for admin_id in ADMIN_IDS[:2]:  # Notify first 2 admins only
                    try:
                        await error_bot.send_message(
                            chat_id=admin_id,
                            text=error_message,
                            parse_mode='Markdown'
                        )
                    except:
                        pass  # Ignore notification errors
        except:
            pass  # Ignore all errors in error notification
        
        sys.