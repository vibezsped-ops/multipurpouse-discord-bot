import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'discord_bot.db')

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()

        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                cash INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                bank_capacity INTEGER DEFAULT 1000,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            )
        """)

        con.commit()
    except sqlite3.Error as e:
        print(f"Database error during init: {e}")
    finally:
        if con:
            con.close()

def get_or_create_user(user_id: int):
    """
    Retrieves a user's data from the database.
    If the user does not exist, a new entry is created with default values.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row  # This allows accessing columns by name
        cur = con.cursor()

        # Check if user exists
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_data = cur.fetchone()

        if user_data is None:
            # User does not exist, create a new entry
            cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            con.commit()

            # Fetch the newly created user
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = cur.fetchone()

        return user_data

    except sqlite3.Error as e:
        print(f"Database error in get_or_create_user: {e}")
        return None
    finally:
        if con:
            con.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
    # Example usage:
    # test_user = get_or_create_user(123456789)
    # if test_user:
    #     print(f"User ID: {test_user['user_id']}, Cash: {test_user['cash']}")
