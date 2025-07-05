#!/usr/bin/env python3
"""
PNP Television Bot - Entry Point with Smart Handler System
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Main function using smart handler system"""
    try:
        logger.info("Starting PNP Television Bot with Smart Handlers...")
        
        from bot.config import BOT_TOKEN
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not configured!")
            sys.exit(1)
        
        logger.info("Bot token configured")
        
        # Use the smart handler system from bot/start.py
        from bot.start import main as smart_main
        await smart_main()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)