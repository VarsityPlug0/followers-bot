# ============================================
# DATABASE — SQLite for users and orders
# ============================================

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            telegram_id INTEGER NOT NULL,
            package_id TEXT NOT NULL,
            service_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            link TEXT NOT NULL,
            panel_order_id INTEGER,
            amount_cents INTEGER NOT NULL,
            payment_method TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            stripe_session_id TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    # Migration: add payment_method column if missing (for existing DBs)
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT "pending"')
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()


# ─── Users ───

def get_or_create_user(telegram_id, username=None):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
    if not user:
        conn.execute('INSERT INTO users (telegram_id, username) VALUES (?, ?)',
                     (telegram_id, username))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
    elif username:
        conn.execute('UPDATE users SET username = ? WHERE telegram_id = ?', (username, telegram_id))
        conn.commit()
    conn.close()
    return dict(user)


# ─── Orders ───

def create_order(telegram_id, package_id, service_name, quantity, link, amount_cents, payment_method='pending'):
    conn = get_db()
    user = conn.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
    cur = conn.execute('''
        INSERT INTO orders (user_id, telegram_id, package_id, service_name, quantity, link, amount_cents, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user['id'], telegram_id, package_id, service_name, quantity, link, amount_cents, payment_method))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id


def update_order_panel_id(order_id, panel_order_id):
    conn = get_db()
    conn.execute('UPDATE orders SET panel_order_id = ?, status = ? WHERE id = ?',
                 (panel_order_id, 'processing', order_id))
    conn.commit()
    conn.close()


def update_order_status(order_id, status):
    conn = get_db()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()


def get_order(order_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_orders(telegram_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC', (telegram_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_orders():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM orders WHERE status IN ("pending", "processing") ORDER BY created_at ASC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Transactions ───

def add_transaction(telegram_id, ttype, amount_cents, stripe_session_id=None, description=None):
    conn = get_db()
    conn.execute('''
        INSERT INTO transactions (telegram_id, type, amount_cents, stripe_session_id, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (telegram_id, ttype, amount_cents, stripe_session_id, description))
    conn.commit()
    conn.close()


def total_revenue():
    conn = get_db()
    row = conn.execute('SELECT COALESCE(SUM(amount_cents), 0) as total FROM transactions').fetchone()
    conn.close()
    return row['total']


def get_pending_payment_orders():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM orders WHERE status = "pending" ORDER BY created_at ASC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def total_orders():
    conn = get_db()
    row = conn.execute('SELECT COUNT(*) as count FROM orders').fetchone()
    conn.close()
    return row['count']
