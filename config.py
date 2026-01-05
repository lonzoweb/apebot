"""
Configuration file for Discord Bot
Contains environment variables and constants
"""

import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
OPENCAGE_KEY = os.getenv("OPENCAGE_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "google_credentials.json")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if os.path.exists(GOOGLE_CREDENTIALS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH

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

# Pink Vote System
MASOCHIST_ROLE_ID = 1167184822129664113
VOTE_THRESHOLD = 7
ROLE_DURATION_SECONDS = 172800 # 48 hours

# Role Aliases for .gr command
ROLE_ALIASES = {
    "niggapass": 1168965931918176297,
    "trial": 1444477594698514594,
    "masochist": 1167184822129664113,
    "hoe": 1168293630570676354,
    "vip": 1234567890123456793,
}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_FILE = "/app/data/quotes.db"
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# ============================================================
# BOT CONFIGURATION
# ============================================================

COMMAND_PREFIX = "."
