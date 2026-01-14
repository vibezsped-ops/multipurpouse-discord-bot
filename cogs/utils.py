import discord
from datetime import datetime, timedelta
import sqlite3
import os

# --- Database Path ---
# This ensures a consistent path to the database from this utility file.
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database')
DB_PATH = os.path.join(DB_DIR, 'discord_bot.db')

# --- Embed Generation ---
# (Embed functions remain the same as before)
def create_success_embed(title: str, description: str, user: discord.Member):
    embed = discord.Embed(title=f"✅ {title}", description=description, color=discord.Color.green())
    embed.set_footer(text=f"Requested by {user.name}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
    embed.timestamp = datetime.utcnow()
    return embed

def create_error_embed(description: str):
    embed = discord.Embed(title="❌ Error", description=description, color=discord.Color.dark_red())
    return embed

def create_economy_embed(title: str, description: str, user: discord.Member):
    embed = discord.Embed(title=f"💰 {title}", description=description, color=discord.Color.gold())
    embed.set_footer(text=f"Requested by {user.name}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
    embed.timestamp = datetime.utcnow()
    return embed

# --- Persistent Cooldown Handling ---

def get_cooldown(user_id: int, command_name: str):
    """
    Checks if a user is on cooldown for a specific command.
    Returns the remaining time if on cooldown, otherwise None.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT expires_at FROM cooldowns WHERE user_id = ? AND command_name = ?", (user_id, command_name))
        result = cur.fetchone()

        if result:
            expires_at = datetime.fromisoformat(result[0])
            if datetime.utcnow() < expires_at:
                remaining = expires_at - datetime.utcnow()
                return remaining
    except sqlite3.Error as e:
        print(f"Database error in get_cooldown: {e}")
    finally:
        if con:
            con.close()
    return None

def set_cooldown(user_id: int, command_name: str, seconds: int):
    """
    Sets a cooldown for a user on a specific command.
    """
    expires_at = datetime.utcnow() + timedelta(seconds=seconds)
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        # Use INSERT OR REPLACE to either create a new cooldown or update an existing one
        cur.execute("""
            INSERT INTO cooldowns (user_id, command_name, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, command_name) DO UPDATE SET
            expires_at=excluded.expires_at;
        """, (user_id, command_name, expires_at.isoformat()))
        con.commit()
    except sqlite3.Error as e:
        print(f"Database error in set_cooldown: {e}")
    finally:
        if con:
            con.close()

def format_time_remaining(time_delta: timedelta):
    """
    Formats a timedelta object into a human-readable string (e.g., '1h 23m 45s').
    """
    seconds = int(time_delta.total_seconds())
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)
