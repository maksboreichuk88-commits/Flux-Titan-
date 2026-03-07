#!/usr/bin/env python3
"""
Telegram News Automation Bot
Entry point wrapper for the flux_titan package.
"""

import sys
import os

# Add the src directory to the python path so the flux_titan package can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from flux_titan.cli import run_cli
except ImportError as e:
    print(f"Error importing flux_titan package: {e}")
    sys.exit(1)

if __name__ == "__main__":
    run_cli()
