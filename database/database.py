import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'discord_bot.db')

DEFAULT_ITEMS = [
    ('Bank Note', 'Increases your bank capacity by 5,000.', 10000, 'Booster', 'bank_capacity_5000'),
    ('Lucky Clover', 'Temporarily increases your luck for gambling.', 5000, 'Booster', 'luck_boost_10'),
    ('Padlock', 'Protects you from being robbed for 24 hours.', 25000, 'Protection', 'rob_protection_24h'),
    ('XP Cookie', 'Doubles your XP gain for 1 hour.', 15000, 'Booster', 'xp_boost_2x_1h'),
]

def init_db():
    """Initializes the database and creates/updates tables as needed."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, cash INTEGER DEFAULT 0, bank INTEGER DEFAULT 0, bank_capacity INTEGER DEFAULT 1000, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, daily_streak INTEGER DEFAULT 0, last_daily TEXT, weekly_streak INTEGER DEFAULT 0, last_weekly TEXT, monthly_streak INTEGER DEFAULT 0, last_monthly TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT, price INTEGER NOT NULL, item_type TEXT, effect TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS inventories (inventory_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_id INTEGER, quantity INTEGER DEFAULT 1, FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(item_id) REFERENCES items(item_id))")
        cur.execute("CREATE TABLE IF NOT EXISTS cooldowns (cooldown_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, command_name TEXT NOT NULL, expires_at TEXT NOT NULL, UNIQUE(user_id, command_name))")

        # Populate default items
        cur.executemany("INSERT OR IGNORE INTO items (name, description, price, item_type, effect) VALUES (?, ?, ?, ?, ?)", DEFAULT_ITEMS)

        con.commit()
    except sqlite3.Error as e:
        print(f"Database error during init: {e}")
    finally:
        if con:
            con.close()

def get_or_create_user(user_id: int):
    try:
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_data = cur.fetchone()
        if user_data is None:
            cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,)); con.commit()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)); user_data = cur.fetchone()
        return user_data
    except sqlite3.Error as e: print(f"DB error in get_or_create_user: {e}"); return None
    finally:
        if con: con.close()

def update_balance(user_id: int, cash_delta: int = 0, bank_delta: int = 0):
    try:
        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("UPDATE users SET cash = cash + ?, bank = bank + ? WHERE user_id = ?", (cash_delta, bank_delta, user_id)); con.commit()
        return True
    except sqlite3.Error as e: print(f"DB error in update_balance: {e}"); return False
    finally:
        if con: con.close()

def update_user_streak(user_id: int, streak_type: str, new_streak: int, new_last_claim: str):
    last_claim_column = f"last_{streak_type}"; streak_column = f"{streak_type}_streak"
    if streak_type not in ['daily', 'weekly', 'monthly']: print(f"Invalid streak_type: {streak_type}"); return False
    try:
        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        query = f"UPDATE users SET {streak_column} = ?, {last_claim_column} = ? WHERE user_id = ?"
        cur.execute(query, (new_streak, new_last_claim, user_id)); con.commit()
        return True
    except sqlite3.Error as e: print(f"DB error in update_user_streak: {e}"); return False
    finally:
        if con: con.close()

# --- New Shop and Inventory Functions ---
def get_shop_items():
    """Retrieves all items available in the shop."""
    try:
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; cur = con.cursor()
        cur.execute("SELECT * FROM items ORDER BY price ASC"); return cur.fetchall()
    except sqlite3.Error as e: print(f"DB error in get_shop_items: {e}"); return []
    finally:
        if con: con.close()

def get_item_by_name(item_name: str):
    """Retrieves a single item by its name."""
    try:
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; cur = con.cursor()
        cur.execute("SELECT * FROM items WHERE name = ?", (item_name,)); return cur.fetchone()
    except sqlite3.Error as e: print(f"DB error in get_item_by_name: {e}"); return None
    finally:
        if con: con.close()

def get_user_inventory(user_id: int):
    """Retrieves a user's inventory with item details."""
    try:
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; cur = con.cursor()
        cur.execute("""
            SELECT i.name, i.description, inv.quantity
            FROM inventories inv
            JOIN items i ON inv.item_id = i.item_id
            WHERE inv.user_id = ?
            ORDER BY i.name ASC
        """, (user_id,)); return cur.fetchall()
    except sqlite3.Error as e: print(f"DB error in get_user_inventory: {e}"); return []
    finally:
        if con: con.close()

def add_item_to_inventory(user_id: int, item_id: int, quantity: int = 1):
    """Adds a specified quantity of an item to a user's inventory."""
    try:
        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        cur.execute("SELECT inventory_id FROM inventories WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        result = cur.fetchone()
        if result:
            cur.execute("UPDATE inventories SET quantity = quantity + ? WHERE inventory_id = ?", (quantity, result[0]))
        else:
            cur.execute("INSERT INTO inventories (user_id, item_id, quantity) VALUES (?, ?, ?)", (user_id, item_id, quantity))
        con.commit(); return True
    except sqlite3.Error as e: print(f"DB error in add_item_to_inventory: {e}"); return False
    finally:
        if con: con.close()

if __name__ == '__main__':
    init_db()
    print("Database schema upgraded and initialized successfully.")
