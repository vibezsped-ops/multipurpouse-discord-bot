import sqlite3
import os
from datetime import datetime

# (Constants and init_db are unchanged)
DB_DIR = os.path.dirname(os.path.abspath(__file__)); DB_PATH = os.path.join(DB_DIR, 'discord_bot.db')
DEFAULT_ITEMS = [('Bank Note', 'Increases bank capacity by 5,000.', 10000, 'Booster', 'bank_capacity_5000'), ('Lucky Clover', 'Increases gambling luck.', 5000, 'Booster', 'luck_boost_10')]

def init_db():
    try:
        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, cash INTEGER DEFAULT 0, bank INTEGER DEFAULT 0, bank_capacity INTEGER DEFAULT 1000, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, daily_streak INTEGER DEFAULT 0, last_daily TEXT, weekly_streak INTEGER DEFAULT 0, last_weekly TEXT, monthly_streak INTEGER DEFAULT 0, last_monthly TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT, price INTEGER NOT NULL, item_type TEXT, effect TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS inventories (inventory_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_id INTEGER, quantity INTEGER DEFAULT 1, FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(item_id) REFERENCES items(item_id))")
        cur.execute("CREATE TABLE IF NOT EXISTS cooldowns (cooldown_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, command_name TEXT NOT NULL, expires_at TEXT NOT NULL, UNIQUE(user_id, command_name))")
        cur.executemany("INSERT OR IGNORE INTO items (name, description, price, item_type, effect) VALUES (?, ?, ?, ?, ?)", DEFAULT_ITEMS)
        con.commit()
    finally:
        if con: con.close()

def get_or_create_user(user_id: int):
    # (Unchanged)
    try:
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)); user_data = cur.fetchone()
        if user_data is None: cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,)); con.commit(); cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)); user_data = cur.fetchone()
        return user_data
    finally:
        if con: con.close()

def update_balance(user_id: int, cash_delta: int = 0, bank_delta: int = 0) -> bool:
    # (Unchanged)
    try:
        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("UPDATE users SET cash = cash + ?, bank = bank + ? WHERE user_id = ? AND cash + ? >= 0 AND bank + ? >= 0", (cash_delta, bank_delta, user_id, cash_delta, bank_delta))
        con.commit()
        return con.total_changes > 0
    finally:
        if con: con.close()

def transfer_cash(sender_id: int, receiver_id: int, amount: int) -> bool:
    """
    Atomically transfers cash from a sender to a receiver.
    Returns True on success, False on failure (e.g., insufficient funds).
    """
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute("BEGIN TRANSACTION")

        # 1. Debit the sender (atomic check)
        cur.execute("UPDATE users SET cash = cash - ? WHERE user_id = ? AND cash >= ?", (amount, sender_id, amount))
        if cur.rowcount == 0:
            con.rollback() # Insufficient funds
            return False

        # 2. Credit the receiver
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (receiver_id,))
        cur.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (amount, receiver_id))

        con.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error in transfer_cash: {e}"); con.rollback(); return False
    finally:
        if con: con.close()

# --- Other functions are unchanged ---
def buy_item(user_id: int, item_id: int, price: int, quantity: int = 1) -> bool:
    # (Unchanged)
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor(); cur.execute("BEGIN TRANSACTION")
        cur.execute("UPDATE users SET cash = cash - ? WHERE user_id = ? AND cash >= ?", (price * quantity, user_id, price * quantity));
        if cur.rowcount == 0: con.rollback(); return False
        cur.execute("SELECT inventory_id FROM inventories WHERE user_id = ? AND item_id = ?", (user_id, item_id)); result = cur.fetchone()
        if result: cur.execute("UPDATE inventories SET quantity = quantity + ? WHERE inventory_id = ?", (quantity, result[0]))
        else: cur.execute("INSERT INTO inventories (user_id, item_id, quantity) VALUES (?, ?, ?)", (user_id, item_id, quantity))
        con.commit(); return True
    except sqlite3.Error as e: print(f"DB error in buy_item: {e}"); con.rollback(); return False
    finally:
        if con: con.close()

def get_shop_items():
    # (Unchanged)
    try:
        con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row; cur = con.cursor()
        cur.execute("SELECT * FROM items ORDER BY price ASC"); return cur.fetchall()
    finally:
        if con: con.close()

if __name__ == '__main__':
    init_db()
