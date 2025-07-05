#!/usr/bin/env python3
"""
Admin panel runner for supervisor
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from bot.admin_panel import app
    import uvicorn
    
    if __name__ == "__main__":
        port = int(os.getenv("ADMIN_PORT", 8080))
        host = os.getenv("ADMIN_HOST", "0.0.0.0")
        
        print(f"Starting admin panel on {host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="info")
        
except ImportError as e:
    print(f"Error importing admin panel: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error starting admin panel: {e}")
    sys.exit(1)