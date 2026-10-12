import sqlite3

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            sant INTEGER DEFAULT 0,
            last_claim TEXT
        )
    ''')
    
    # جدول کدهای هدیه
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            count INTEGER,
            amount INTEGER
        )
    ''')
    
    # جدول استفاده از کدهای هدیه
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS used_promos (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )
    ''')
    
    # جدول بازی‌های فعال
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER,
            amount INTEGER,
            message_id INTEGER,
            chat_id INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id, username=""):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT sant, last_claim FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, username, sant) VALUES (?, ?, ?)', (user_id, username, 0))
        conn.commit()
        user = (0, None)
    conn.close()
    return user

def update_sant(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET sant = sant + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
