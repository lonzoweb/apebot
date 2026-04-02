from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aiosqlite
import os
import sys
import json
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

# Add parent dir to sys.path to import from database.py if needed, 
# but better to have standalone DB logic here for safety or import it.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import DB_FILE, GUILD_ID
from database import calculate_level_for_xp, get_cached_roles, init_db, get_cached_channels
from database import get_all_item_prices, set_item_price
import database
from items import ITEM_REGISTRY

import logging
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    """Run DB init on startup to ensure all tables exist."""
    await init_db()
    logger.info("✅ Dashboard DB tables verified on startup.")
    yield

app = FastAPI(title="Apebot Leveling Dashboard API", lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_methods=["*"],
    allow_headers=["*"],
)

class SettingUpdate(BaseModel):
    key: str
    value: str

class MultiplierUpdate(BaseModel):
    target_id: str
    multiplier: float

class RewardUpdate(BaseModel):
    level: int
    role_id: str
    stack_role: int = 1

class QuoteDropSettings(BaseModel):
    quote_drops_enabled: bool
    quote_drops_interval_hours: float

class QuoteDropSendReq(BaseModel):
    drop_id: Optional[int] = None

@app.get("/stats")
async def get_stats():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT COUNT(*) FROM users_xp") as cursor:
            count = await cursor.fetchone()
        async with db.execute("SELECT SUM(xp) FROM users_xp") as cursor:
            total_xp = await cursor.fetchone()
        return {
            "total_users": count[0] if count else 0,
            "total_xp": total_xp[0] if total_xp else 0
        }

@app.get("/settings")
async def get_settings():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT key, value FROM level_settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

@app.post("/settings")
async def update_setting(update: SettingUpdate):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO level_settings (key, value) VALUES (?, ?)", (update.key, update.value))
        await db.commit()
    return {"status": "ok"}

@app.get("/multipliers")
async def get_multipliers():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT target_id, multiplier FROM level_multipliers") as cursor:
            rows = await cursor.fetchall()
            return [{"target_id": row[0], "multiplier": row[1]} for row in rows]

@app.post("/multipliers")
async def update_multiplier(update: MultiplierUpdate):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO level_multipliers (target_id, multiplier) VALUES (?, ?)", (update.target_id, update.multiplier))
        await db.commit()
    return {"status": "ok"}

@app.delete("/multipliers/{target_id}")
async def delete_multiplier(target_id: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM level_multipliers WHERE target_id = ?", (target_id,))
        await db.commit()
    return {"status": "ok"}

@app.get("/rewards")
async def get_rewards():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT level, role_id, stack_role FROM reward_roles") as cursor:
            rows = await cursor.fetchall()
            return [{"level": row[0], "role_id": row[1], "stack_role": bool(row[2])} for row in rows]

@app.post("/rewards")
async def update_reward(update: RewardUpdate):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO reward_roles (level, role_id, stack_role) VALUES (?, ?, ?)", 
            (update.level, update.role_id, update.stack_role)
        )
        await db.commit()
    return {"status": "ok"}

@app.delete("/rewards/{level}")
async def delete_reward(level: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM reward_roles WHERE level = ?", (level,))
        await db.commit()
    return {"status": "ok"}

@app.get("/leaderboard")
async def get_leaderboard(limit: int = 50):
    async with aiosqlite.connect(DB_FILE) as db:
        # Join with profile cache to get usernames
        query = """
            SELECT u.user_id, u.xp, u.level, p.username, p.avatar_url 
            FROM users_xp u
            LEFT JOIN user_profile_cache p ON u.user_id = p.user_id
            ORDER BY u.level DESC, u.xp DESC 
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": row[0], 
                    "xp": row[1], 
                    "level": row[2], 
                    "username": row[3] or f"User {row[0]}", 
                    "avatar": row[4]
                } for row in rows
            ]

@app.get("/roles")
async def get_roles():
    """Returns cached server roles for resolution."""
    return await get_cached_roles()

@app.get("/channels")
async def get_channels():
    """Returns cached server channels for resolution."""
    return await get_cached_channels()

@app.get("/export")
async def export_data():
    """Export data in Polaris-compliant JSON format."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Get users
        async with db.execute("SELECT user_id, xp FROM users_xp") as cursor:
            rows = await cursor.fetchall()
            users_data = {row[0]: {"xp": row[1]} for row in rows}
        
        # Get settings
        async with db.execute("SELECT key, value FROM level_settings") as cursor:
            rows = await cursor.fetchall()
            settings_data = {row[0]: row[1] for row in rows}
            
        return {
            "users": users_data,
            "settings": settings_data
        }

@app.post("/import")
async def import_data(jsonData: Dict[str, Any]):
    """Import data in Polaris-compliant JSON format."""
    details = []
    imported_users = 0
    
    # Polaris handles 'xp' as an alias for 'users'
    users = jsonData.get("users") or jsonData.get("xp")
    
    # If it's just a raw dict of users without the 'users' key
    if not users and not jsonData.get("settings") and isinstance(jsonData, dict):
        users = jsonData

    async with aiosqlite.connect(DB_FILE) as db:
        # Get settings for level calculation
        async with db.execute("SELECT key, value FROM level_settings") as cursor:
            rows = await cursor.fetchall()
            settings = {row[0]: row[1] for row in rows}
            
        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        r = int(settings.get("rounding", 100))

        if users:
            for user_id, data in users.items():
                xp = data.get("xp") if isinstance(data, dict) else data
                if xp is not None:
                    lvl = calculate_level_for_xp(int(xp), c3, c2, c1, r)
                    await db.execute(
                        """
                        INSERT INTO users_xp (user_id, xp, level, last_xp_time)
                        VALUES (?, ?, ?, 0)
                        ON CONFLICT(user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level
                        """,
                        (str(user_id), int(xp), lvl)
                    )
                    
                    # 👤 Capture username/avatar if available in the migration JSON
                    if isinstance(data, dict):
                        username = data.get("username") or data.get("name")
                        avatar = data.get("avatar") or data.get("avatar_url")
                        if username:
                            await db.execute(
                                """
                                INSERT INTO user_profile_cache (user_id, username, avatar_url, last_updated)
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT(user_id) DO UPDATE SET 
                                    username = excluded.username, 
                                    avatar_url = excluded.avatar_url,
                                    last_updated = excluded.last_updated
                                """,
                                (str(user_id), str(username), str(avatar) if avatar else None, int(time.time()))
                            )

                    imported_users += 1
            details.append(f"{imported_users} users")

        if "settings" in jsonData:
            s = jsonData["settings"]
            # Polaris flattening
            if "curve" in s and isinstance(s["curve"], dict):
                for k, v in s["curve"].items():
                    target_key = f"c{k}" # '1' -> 'c1'
                    await db.execute("INSERT OR REPLACE INTO level_settings (key, value) VALUES (?, ?)", (target_key, str(v)))
            
            # Save other top-level settings
            for k, v in s.items():
                if k != "curve":
                    await db.execute("INSERT OR REPLACE INTO level_settings (key, value) VALUES (?, ?)", (k, str(v)))
            details.append("Server settings")
            
        await db.commit()
    
    if not details:
        raise HTTPException(status_code=400, detail="No valid JSON data found!")
        
    return {"status": "ok", "details": details}

@app.post("/recalculate")
async def recalculate_all_levels():
    """Recalculate levels for everyone based on current settings."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT key, value FROM level_settings") as cursor:
            rows = await cursor.fetchall()
            settings = {row[0]: row[1] for row in rows}
            
        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        r = int(settings.get("rounding", 100))

        async with db.execute("SELECT user_id, xp FROM users_xp") as cursor:
            users = await cursor.fetchall()

        count = 0
        for user_id, xp in users:
            lvl = calculate_level_for_xp(xp, c3, c2, c1, r)
            await db.execute("UPDATE users_xp SET level = ? WHERE user_id = ?", (lvl, user_id))
            count += 1
            
        await db.commit()
    return {"status": "ok", "count": count}

class BatchSettingsUpdate(BaseModel):
    settings: Dict[str, str]

@app.post("/settings/batch")
async def batch_update_settings(update: BatchSettingsUpdate):
    """Batch update multiple settings at once (for the save button)."""
    async with aiosqlite.connect(DB_FILE) as db:
        for key, value in update.settings.items():
            await db.execute("INSERT OR REPLACE INTO level_settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()
    return {"status": "ok", "count": len(update.settings)}

@app.post("/clear-xp")
async def clear_all_xp():
    """Reset all users' XP and level to 0."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE users_xp SET xp = 0, level = 0")
        await db.commit()
    return {"status": "ok"}

@app.post("/reset-settings")
async def reset_settings():
    """Delete all level settings so the bot reinitializes defaults."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM level_settings")
        await db.execute("DELETE FROM level_multipliers")
        await db.execute("DELETE FROM reward_roles")
        await db.commit()
    return {"status": "ok"}

class PruneRequest(BaseModel):
    threshold: int = 100

@app.post("/prune")
async def prune_members(req: PruneRequest):
    """Delete users with XP below the threshold."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT COUNT(*) FROM users_xp WHERE xp < ?", (req.threshold,)) as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0
        await db.execute("DELETE FROM users_xp WHERE xp < ?", (req.threshold,))
        await db.commit()
    return {"status": "ok", "deleted": count}

@app.get("/export/csv")
async def export_csv():
    """Export user XP as CSV."""
    from fastapi.responses import PlainTextResponse
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, xp, level FROM users_xp ORDER BY level DESC, xp DESC") as cursor:
            rows = await cursor.fetchall()
    lines = ["user_id,xp,level"] + [f"{r[0]},{r[1]},{r[2]}" for r in rows]
    return PlainTextResponse("\n".join(lines), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=apeiron_export.csv"})

@app.get("/export/txt")
async def export_txt():
    """Export user XP as plain text."""
    from fastapi.responses import PlainTextResponse
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, xp, level FROM users_xp ORDER BY level DESC, xp DESC") as cursor:
            rows = await cursor.fetchall()
    lines = [f"UserID: {r[0]} | XP: {r[1]} | Level: {r[2]}" for r in rows]
    return PlainTextResponse("\n".join(lines), media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=apeiron_export.txt"})

# ============================================================
# DAILY QUOTES MANAGEMENT (existing .quote system)
# ============================================================

class QuoteAdd(BaseModel):
    quote: str

@app.get("/quotes")
async def get_quotes():
    """Return all daily quotes."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT id, quote FROM quotes ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [{"id": row[0], "quote": row[1]} for row in rows]

@app.post("/quotes")
async def add_quote(data: QuoteAdd):
    """Add a new daily quote."""
    if not data.quote.strip():
        raise HTTPException(status_code=400, detail="Quote cannot be empty.")
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO quotes (quote) VALUES (?)", (data.quote.strip(),))
        await db.commit()
    return {"status": "ok"}

@app.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: int):
    """Delete a daily quote by ID."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        await db.commit()
    return {"status": "ok"}

# ============================================================
# QUOTE DROPS (new =quote / random drop system)
# ============================================================

class QuoteDropAdd(BaseModel):
    quote: str

class QuoteDropSetting(BaseModel):
    quote_drops_per_day: int

@app.get("/quote-drops")
async def get_quote_drops():
    """Return all quote drops."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT id, quote, added_by, added_at FROM quote_drops ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [{"id": row[0], "quote": row[1], "added_by": row[2], "added_at": row[3]} for row in rows]

@app.post("/quote-drops")
async def add_quote_drop_endpoint(data: QuoteDropAdd):
    """Add a new quote drop."""
    if not data.quote.strip():
        raise HTTPException(status_code=400, detail="Quote cannot be empty.")
    import time
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR IGNORE INTO quote_drops (quote, added_by, added_at) VALUES (?, ?, ?)",
            (data.quote.strip(), "dashboard", time.time())
        )
        await db.commit()
    return {"status": "ok"}

@app.delete("/quote-drops/{drop_id}")
async def delete_quote_drop_endpoint(drop_id: int):
    """Delete a quote drop by ID."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM quote_drops WHERE id = ?", (drop_id,))
        await db.commit()
    return {"status": "ok"}

@app.get("/quote-drops/settings")
async def get_quote_drop_settings():
    """Get quote drop automated cycle settings."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT setting_key, setting_value FROM global_settings WHERE setting_key IN ('quote_drops_enabled', 'quote_drops_interval_hours')"
        ) as cursor:
            rows = await cursor.fetchall()
            settings = {row[0]: row[1] for row in rows}
            
            return {
                "quote_drops_enabled": settings.get("quote_drops_enabled") == "1",
                "quote_drops_interval_hours": int(settings.get("quote_drops_interval_hours", "8"))
            }

@app.post("/quote-drops/settings")
async def update_quote_drop_settings(data: QuoteDropSettings):
    """Update quote drop automated cycle settings."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO global_settings (setting_key, setting_value) VALUES ('quote_drops_enabled', ?)",
            ('1' if data.quote_drops_enabled else '0',)
        )
        await db.execute(
            "INSERT OR REPLACE INTO global_settings (setting_key, setting_value) VALUES ('quote_drops_interval_hours', ?)",
            (str(data.quote_drops_interval_hours),)
        )
        await db.commit()
    return {"status": "ok"}

class QuoteDropSendReq(BaseModel):
    drop_id: Optional[int] = None

@app.post("/quote-drops/send")
async def send_quote_drop(req: QuoteDropSendReq):
    """Manually send a quote drop to the configured main channel via Discord REST API."""
    from config import TOKEN
    from database import get_channel_assigns
    
    # Get the target channel from DB config
    assigns = await get_channel_assigns()
    channel_id = assigns.get("main", "")
    if not channel_id:
        raise HTTPException(status_code=400, detail="No 'main' channel configured. Go to Misc tab to set one.")
    
    # Pick the quote
    quote_text = None
    async with aiosqlite.connect(DB_FILE) as db:
        if req.drop_id is not None:
            async with db.execute("SELECT quote FROM quote_drops WHERE id = ?", (req.drop_id,)) as cursor:
                row = await cursor.fetchone()
                if row: quote_text = row[0]
        else:
            async with db.execute("SELECT quote FROM quote_drops ORDER BY RANDOM() LIMIT 1") as cursor:
                row = await cursor.fetchone()
                if row: quote_text = row[0]
                
    if not quote_text:
        raise HTTPException(status_code=404, detail="Quote not found or database empty.")
    
    # Send via Discord REST API
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"},
                json={"content": quote_text}
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    raise HTTPException(status_code=500, detail=f"Discord API error: {resp.status} - {body}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
        
    return {"status": "ok", "sent_quote": quote_text}

# ============================================================
# CHANNEL & COMMAND CONFIGURATION
# ============================================================

from database import (
    get_channel_assigns, set_channel_assign, 
    get_command_restrictions, set_command_restriction
)

@app.get("/channel-config")
async def api_get_channel_config():
    """Get the assigned channel IDs for each role (main, spam, admin, error)."""
    return await get_channel_assigns()

@app.get("/commands")
async def api_get_commands():
    """Get a list of all registered bot commands by scanning cog files."""
    import re
    cmds = set()
    cogs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cogs")
    
    # Improved scanner: Matches command decorators specifically
    decorator_pattern = re.compile(r'@(?:commands|app_commands)\.(?:command|group)\s*(?:\((.*?)\))?', re.DOTALL)
    
    if os.path.isdir(cogs_dir):
        for fname in os.listdir(cogs_dir):
            if fname.endswith(".py"):
                try:
                    with open(os.path.join(cogs_dir, fname), "r") as f:
                        content = f.read()
                    
                    for match in decorator_pattern.finditer(content):
                        args = match.group(1) or ""
                        # Find the associated function name by looking ahead
                        rem = content[match.end():]
                        fn_match = re.search(r'async def\s+([a-zA-Z0-9_]+)', rem)
                        
                        if fn_match:
                            fn_name = fn_match.group(1)
                            # Extract name="xxx" or use function name
                            name_match = re.search(r'name=["\']([^"\']+)["\']', args)
                            cmd_name = name_match.group(1) if name_match else fn_name
                            cmds.add(cmd_name)
                            
                            # Extract aliases=["...", "..."]
                            alias_match = re.search(r'aliases=\[([^\]]+)\]', args)
                            if alias_match:
                                for a in re.finditer(r'["\']([^"\']+)["\']', alias_match.group(1)):
                                    cmds.add(a.group(1))
                except Exception:
                    pass
    return sorted(list(cmds))

@app.get("/command-stats")
async def api_get_command_stats():
    """Get the most used commands from the database."""
    from database import get_command_usage_stats
    return await get_command_usage_stats(limit=15)

class ChannelConfigUpdate(BaseModel):
    role: str
    channel_id: str

@app.post("/channel-config")
async def api_set_channel_config(data: ChannelConfigUpdate):
    """Set the assigned channel ID for a role."""
    await set_channel_assign(data.role, data.channel_id)
    return {"status": "ok"}

@app.get("/command-restrictions")
async def api_get_command_restrictions():
    """Get which commands are allowed in which channel roles."""
    return await get_command_restrictions()

class CommandRestrictionUpdate(BaseModel):
    command_name: str
    role: str
    is_allowed: bool

@app.post("/command-restrictions")
async def api_set_command_restriction(data: CommandRestrictionUpdate):
    """Enable or disable a command in a specific channel role."""
    await set_command_restriction(data.command_name, data.role, data.is_allowed)
    return {"status": "ok"}

# ============================================================
# HALL OF FAME SETTINGS
# ============================================================

@app.get("/hof-settings")
async def api_get_hof_settings():
    """Get Hall of Fame settings (single-guild)."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT guild_id, channel_id, threshold, emojis, "
            "ignored_channels, blacklisted_users FROM hof_settings WHERE guild_id = ?",
            (str(GUILD_ID),)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return {"guild_id": str(GUILD_ID), "channel_id": "", "threshold": 3, "emojis": ["⭐"], "ignored_channels": [], "blacklisted_users": []}
    return {
        "guild_id": row[0],
        "channel_id": row[1] or "",
        "threshold": row[2],
        "emojis": json.loads(row[3]),
        "ignored_channels":  json.loads(row[4]),
        "blacklisted_users": json.loads(row[5]) if row[5] else [],
    }

class HofSettingsUpdate(BaseModel):
    channel_id: Optional[str] = None
    threshold: Optional[int] = None
    emojis: Optional[list] = None
    ignored_channels: Optional[list] = None
    blacklisted_users: Optional[list] = None

@app.post("/hof-settings")
async def api_set_hof_settings(data: HofSettingsUpdate):
    """Update Hall of Fame settings. Only provided fields are updated."""
    # Get current settings first
    current = await api_get_hof_settings()
    guild_id = str(GUILD_ID)
    
    channel_id = data.channel_id if data.channel_id is not None else current["channel_id"]
    threshold = data.threshold if data.threshold is not None else current["threshold"]
    emojis = data.emojis if data.emojis is not None else current["emojis"]
    ignored_channels = data.ignored_channels if data.ignored_channels is not None else current["ignored_channels"]
    blacklisted_users = data.blacklisted_users if data.blacklisted_users is not None else current["blacklisted_users"]
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            INSERT INTO hof_settings
                (guild_id, channel_id, threshold, emojis,
                 ignored_channels, locked_messages, trashed_messages, blacklisted_users)
            VALUES (?, ?, ?, ?, ?, '[]', '[]', ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id         = excluded.channel_id,
                threshold          = excluded.threshold,
                emojis             = excluded.emojis,
                ignored_channels   = excluded.ignored_channels,
                blacklisted_users  = excluded.blacklisted_users
            """,
            (guild_id, channel_id, threshold,
             json.dumps(emojis),
             json.dumps(ignored_channels), json.dumps(blacklisted_users)),
        )
        await db.commit()
    return {"status": "ok"}



# ==========================================
# .key COMMAND SETTINGS
# ==========================================

class KeyImageAdd(BaseModel):
    url: str
    label: Optional[str] = ""

class KeyConfigUpdate(BaseModel):
    send_count_user: int
    send_count_admin: int

@app.get("/key-settings")
async def api_get_key_settings():
    from database import get_key_settings
    return await get_key_settings()

@app.post("/key-settings/config")
async def api_set_key_config(data: KeyConfigUpdate):
    from database import set_key_config
    if data.send_count_user < 1 or data.send_count_admin < 1:
        raise HTTPException(status_code=400, detail="Send counts must be >= 1")
    await set_key_config(data.send_count_user, data.send_count_admin)
    return {"status": "ok"}

@app.post("/key-settings/images")
async def api_add_key_image(data: KeyImageAdd):
    from database import add_key_image
    await add_key_image(data.url, data.label or "")
    return {"status": "ok"}

@app.delete("/key-settings/images/{image_id}")
async def api_delete_key_image(image_id: int):
    from database import delete_key_image
    await delete_key_image(image_id)
    return {"status": "ok"}

@app.post("/key-settings/images/{image_id}/activate")
async def api_activate_key_image(image_id: int):
    from database import set_key_active_image
    await set_key_active_image(image_id)
    return {"status": "ok"}


# ==========================================
# ADMIN CONFIG (Tarot, Economy, Yap)
# ==========================================

class AdminConfigUpdate(BaseModel):
    tarot_deck: Optional[str] = None      # "thoth" | "rws" | "manara"
    economy_enabled: Optional[bool] = None
    yap_level: Optional[str] = None       # "low" | "high"

@app.get("/admin-config")
async def api_get_admin_config():
    """Return all admin-configurable settings in one call."""
    from database import is_economy_on, get_yap_level, get_guild_tarot_deck
    guild_id = str(GUILD_ID)
    economy = await is_economy_on()
    yap = await get_yap_level()
    tarot = await get_guild_tarot_deck(guild_id)
    return {
        "economy_enabled": economy,
        "yap_level": yap,
        "tarot_deck": tarot,
    }

@app.post("/admin-config")
async def api_set_admin_config(data: AdminConfigUpdate):
    """Update admin settings. Only provided fields are changed."""
    from database import set_economy_status, set_yap_level, set_guild_tarot_deck
    guild_id = str(GUILD_ID)

    if data.economy_enabled is not None:
        await set_economy_status(data.economy_enabled)

    if data.yap_level is not None:
        if data.yap_level not in ("low", "high"):
            raise HTTPException(status_code=400, detail="yap_level must be 'low' or 'high'")
        await set_yap_level(data.yap_level)

    if data.tarot_deck is not None:
        if data.tarot_deck not in ("thoth", "rws", "manara"):
            raise HTTPException(status_code=400, detail="Invalid deck name")
        await set_guild_tarot_deck(guild_id, data.tarot_deck)

    return {"status": "ok"}

# ============================================================
# QUOTE SCHEDULE (configurable post times)
# ============================================================

class QuoteScheduleUpdate(BaseModel):
    morning_hour: int  # 0-23
    evening_hour: int  # 0-23

@app.get("/quote-schedule")
async def api_get_quote_schedule():
    """Get configured daily quote post hours."""
    morning = await database.get_setting("quote_morning_hour", "10")
    evening = await database.get_setting("quote_evening_hour", "18")
    return {"morning_hour": int(morning), "evening_hour": int(evening)}

@app.post("/quote-schedule")
async def api_set_quote_schedule(data: QuoteScheduleUpdate):
    """Save daily quote post hours (0-23)."""
    if not (0 <= data.morning_hour <= 23 and 0 <= data.evening_hour <= 23):
        raise HTTPException(status_code=400, detail="Hours must be 0-23")
    await database.set_setting("quote_morning_hour", str(data.morning_hour))
    await database.set_setting("quote_evening_hour", str(data.evening_hour))
    return {"status": "ok"}


# ============================================================
# NUMEROLOGY
# ============================================================

class NumerologySettingsUpdate(BaseModel):
    morning_hour: Optional[int] = None   # 7am default
    evening_hour: Optional[int] = None   # 22 (10pm) default
    channel_id: Optional[str] = None

class NumerologyNumberDesc(BaseModel):
    num: int
    description: str

class NumerologyCombo(BaseModel):
    primary_num: int
    secondary_num: int
    combo_desc: str

class ShopItemUpdate(BaseModel):
    item_key: str
    price: int

@app.get("/numerology/settings")
async def api_get_numerology_settings():
    """Get numerology post schedule and channel config."""
    morning = await database.get_setting("numerology_morning_hour", "7")
    evening = await database.get_setting("numerology_evening_hour", "22")
    channel = await database.get_setting("numerology_channel_id", "")
    return {
        "morning_hour": int(morning),
        "evening_hour": int(evening),
        "channel_id": channel or "",
    }

@app.post("/numerology/settings")
async def api_set_numerology_settings(data: NumerologySettingsUpdate):
    """Save numerology schedule settings."""
    if data.morning_hour is not None:
        if not (0 <= data.morning_hour <= 23):
            raise HTTPException(status_code=400, detail="morning_hour must be 0-23")
        await database.set_setting("numerology_morning_hour", str(data.morning_hour))
    if data.evening_hour is not None:
        if not (0 <= data.evening_hour <= 23):
            raise HTTPException(status_code=400, detail="evening_hour must be 0-23")
        await database.set_setting("numerology_evening_hour", str(data.evening_hour))
    if data.channel_id is not None:
        await database.set_setting("numerology_channel_id", data.channel_id)
    return {"status": "ok"}

@app.get("/numerology/numbers")
async def api_get_numerology_numbers():
    """Get all number descriptions."""
    return await database.get_all_numerology_number_descs()

@app.post("/numerology/numbers")
async def api_set_numerology_number(data: NumerologyNumberDesc):
    """Set description for a numerology number."""
    valid = {1,2,3,4,5,6,7,8,9,11,22,33}
    if data.num not in valid:
        raise HTTPException(status_code=400, detail=f"num must be one of {sorted(valid)}")
    await database.set_numerology_number_desc(data.num, data.description)
    return {"status": "ok"}

@app.get("/numerology/combos")
async def api_get_numerology_combos():
    """Get all combination readings."""
    return await database.get_all_numerology_combos()

@app.post("/numerology/combos")
async def api_set_numerology_combo(data: NumerologyCombo):
    """Set combination reading for a primary+secondary pair."""
    await database.set_numerology_combo(data.primary_num, data.secondary_num, data.combo_desc)
    return {"status": "ok"}

@app.post("/numerology/seed")
async def api_seed_numerology():
    """Manual trigger to seed numerology defaults into DB."""
    await database.seed_numerology_defaults()
    return {"status": "ok"}

@app.get("/shop/items")
async def api_get_shop_items():
    """List all items from registry + current DB prices."""
    try:
        overrides = await get_all_item_prices()
        items = []
        for key, data in ITEM_REGISTRY.items():
            items.append({
                "key": key,
                "name": key.replace('_', ' ').title(),
                "description": data.get("shop_desc", ""),
                "base_price": data.get("cost", 0),
                "current_price": overrides.get(key, data.get("cost", 0))
            })
        logger.info(f"GET /shop/items -> {len(items)} items")
        return items
    except Exception as e:
        logger.exception(f"Error in /shop/items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/shop/items")
async def api_set_item_price(data: ShopItemUpdate):
    """Update price override for an item."""
    await set_item_price(data.item_key, data.price)
    return {"status": "ok"}

@app.get("/deposit-info")
async def api_get_deposit_info():
    """Get the current deposit address/info."""
    value = await database.get_setting("deposit_info", "")
    return {"deposit_info": value}

@app.post("/deposit-info")
async def api_set_deposit_info(data: dict):
    """Save the deposit address/info."""
    value = data.get("deposit_info", "")
    await database.set_setting("deposit_info", value)
    return {"status": "ok"}

@app.get("/bulletin/settings")
async def api_get_bulletin_settings():
    """Get the current bulletin channel settings."""
    channel_id = await database.get_setting("bulletin_channel_id", "")
    purge_enabled = await database.get_setting("weekly_purge_enabled", "0")
    tc_time = await database.get_setting("daily_tc_time", "08:00")
    return {
        "channel_id": channel_id,
        "weekly_purge_enabled": int(purge_enabled),
        "daily_tc_time": tc_time
    }

@app.post("/bulletin/settings")
async def api_set_bulletin_settings(data: dict):
    """Save the bulletin channel settings."""
    if "channel_id" in data:
        await database.set_setting("bulletin_channel_id", str(data["channel_id"]))
    if "weekly_purge_enabled" in data:
        await database.set_setting("weekly_purge_enabled", str(int(data["weekly_purge_enabled"])))
    if "daily_tc_time" in data:
        await database.set_setting("daily_tc_time", str(data["daily_tc_time"]))
    return {"status": "ok"}

@app.get("/numerology/preview")
async def api_numerology_preview(date: Optional[str] = None):
    """
    Preview the numerology reading for a given date (YYYY-MM-DD).
    Defaults to today (LA timezone).
    """
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    import numerology as num_engine
    from datetime import date as _date
    from zoneinfo import ZoneInfo

    if date:
        try:
            target = _date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        from datetime import datetime
        target = datetime.now(ZoneInfo("America/Los_Angeles")).date()

    nums = num_engine.calculate_numerology(target)
    reading = await num_engine.get_reading(target, database)
    return {
        "date": target.isoformat(),
        "primary": nums["primary"],
        "secondary": nums["secondary"],
        "primary_label": num_engine.format_primary_label(nums["primary"]),
        "secondary_label": num_engine.format_secondary_label(nums["secondary"]),
        "reading": reading,
    }


# --- Serve Frontend ---

# Search for frontend/dist relative to project root
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_path = os.path.join(base_dir, "dashboard", "frontend", "dist")

if os.path.exists(frontend_path):
    logger.info(f"✅ Serving frontend from: {frontend_path}")
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    logger.warning(f"⚠️ Frontend 'dist' folder not found at {frontend_path}")
    @app.get("/")
    async def root():
        return {
            "message": "API is running. Frontend 'dist' folder not found. Please build it.",
            "attempted_path": frontend_path
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
