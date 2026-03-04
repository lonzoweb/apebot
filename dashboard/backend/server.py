from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aiosqlite
import os
import sys
import json
from typing import Dict, Any, Optional

# Add parent dir to sys.path to import from database.py if needed, 
# but better to have standalone DB logic here for safety or import it.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import DB_FILE
from database import calculate_level_for_xp, get_cached_roles, init_db

import logging
logger = logging.getLogger(__name__)

app = FastAPI(title="Apebot Leveling Dashboard API")

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
        # Get settings
        async with db.execute("SELECT key, value FROM level_settings") as cursor:
            rows = await cursor.fetchall()
            settings = {row[0]: row[1] for row in rows}
            
        c3 = float(settings.get("c3", 1))
        c2 = float(settings.get("c2", 50))
        c1 = float(settings.get("c1", 100))
        r = int(settings.get("rounding", 100))

        # Get all users
        async with db.execute("SELECT user_id, xp FROM users_xp") as cursor:
            users = await cursor.fetchall()

        count = 0
        for user_id, xp in users:
            lvl = calculate_level_for_xp(xp, c3, c2, c1, r)
            await db.execute("UPDATE users_xp SET level = ? WHERE user_id = ?", (lvl, user_id))
            count += 1
            
        await db.commit()
    return {"status": "ok", "count": count}

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

    import uvicorn
    # Ensure tables exist before starting (crucial for Railway)
    import asyncio
    asyncio.run(init_db())
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
