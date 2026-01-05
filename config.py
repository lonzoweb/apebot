"""
Configuration file for Discord Bot
Contains environment variables and constants
"""

import os

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
OPENCAGE_KEY = os.getenv("OPENCAGE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is missing!")
if not OPENCAGE_KEY:
    raise ValueError("OPENCAGE_KEY environment variable is missing!")
if not SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY environment variable is missing!")

# Channel IDs
channel_id_str = os.getenv("CHANNEL_ID")
if channel_id_str is None:
    raise ValueError("CHANNEL_ID environment variable is missing!")
CHANNEL_ID = int(channel_id_str)

test_channel_id_str = os.getenv("TEST_CHANNEL_ID")
TEST_CHANNEL_ID = int(test_channel_id_str) if test_channel_id_str else None
# Add MOD_CHANNEL_ID
mod_channel_id_str = os.getenv("MOD_CHANNEL_ID")
MOD_CHANNEL_ID = int(mod_channel_id_str) if mod_channel_id_str else None

# ============================================================
# ROLE CONFIGURATIONS
# ============================================================

AUTHORIZED_ROLES = ["Principe", "Capo", "Sottocapo", "Caporegime"]
DAILY_COMMAND_ROLE = "Patrizio"
ROLE_ADD_QUOTE = "Caporegime"

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_FILE = "/app/data/quotes.db"
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# ============================================================
# BOT CONFIGURATION
# ============================================================

COMMAND_PREFIX = "."
