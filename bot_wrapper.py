#!/usr/bin/env python3
"""
Bot wrapper for supervisor
"""

import subprocess
import sys
import os
from pathlib import Path

# Set working directory
os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    # Run the main bot
    subprocess.run([sys.executable, "-u", "run_bot.py"])