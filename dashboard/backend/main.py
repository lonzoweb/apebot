from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
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
        async with db.execute("SELECT level, role_id FROM reward_roles") as cursor:
            rows = await cursor.fetchall()
            return [{"level": row[0], "role_id": row[1]} for row in rows]

@app.post("/rewards")
async def update_reward(update: RewardUpdate):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO reward_roles (level, role_id) VALUES (?, ?)", (update.level, update.role_id))
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
        async with db.execute("SELECT user_id, xp, level FROM users_xp ORDER BY level DESC, xp DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": row[0], "xp": row[1], "level": row[2]} for row in rows]

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
        if users:
            for user_id, data in users.items():
                # Polaris format: user_id is the key, data is {xp: ...}
                xp = data.get("xp") if isinstance(data, dict) else data
                if xp is not None:
                    # We need to calculate level or just set it to 0 and let the bot fix it
                    # For a clean import, setting level to 0 is safest, bot updates it on next message
                    # Or we could implement the cubic formula here too.
                    await db.execute(
                        """
                        INSERT INTO users_xp (user_id, xp, level, last_xp_time)
                        VALUES (?, ?, 0, 0)
                        ON CONFLICT(user_id) DO UPDATE SET xp = excluded.xp
                        """,
                        (str(user_id), int(xp))
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
