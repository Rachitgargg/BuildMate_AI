import sqlite3
import os
from typing import List, Dict, Any

DB_DIR = "/Users/rachit/Desktop/BuildMate AI/database"
DB_PATH = os.path.join(DB_DIR, "startup.db")

def get_connection():
    """Returns a connection to the SQLite database, creating the database directory if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Startup Profile Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS startup_profile (
                id INTEGER PRIMARY KEY DEFAULT 1,
                name TEXT,
                idea TEXT,
                target_audience TEXT,
                tech_stack TEXT,
                estimated_budget TEXT,
                currency TEXT DEFAULT 'USD',
                current_stage TEXT DEFAULT 'Ideation',
                competitor_status TEXT DEFAULT 'Pending',
                budget_status TEXT DEFAULT 'Pending',
                roadmap_status TEXT DEFAULT 'Pending',
                next_task TEXT DEFAULT 'Introduce your startup idea',
                progress_pct INTEGER DEFAULT 10
            )
        """)
        
        # Migration: Add new columns if table already exists without them
        for col, col_type in [
            ("current_stage", "TEXT DEFAULT 'Ideation'"),
            ("competitor_status", "TEXT DEFAULT 'Pending'"),
            ("budget_status", "TEXT DEFAULT 'Pending'"),
            ("roadmap_status", "TEXT DEFAULT 'Pending'"),
            ("next_task", "TEXT DEFAULT 'Introduce your startup idea'"),
            ("progress_pct", "INTEGER DEFAULT 10"),
            ("last_updated", "TEXT DEFAULT 'Never'")
        ]:
            try:
                cursor.execute(f"ALTER TABLE startup_profile ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass # Column already exists
        
        # Ensure there is always exactly one profile row
        cursor.execute("SELECT COUNT(*) FROM startup_profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO startup_profile (id, name, idea, target_audience, tech_stack, estimated_budget, currency, current_stage, competitor_status, budget_status, roadmap_status, next_task, progress_pct)
                VALUES (1, 'Untitled Startup', '', '', '', '₹0', 'INR', 'Ideation', 'Pending', 'Pending', 'Pending', 'Introduce your startup idea', 10)
            """)
            
        # 2. Chat History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Competitors Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                strength TEXT,
                weakness TEXT
            )
        """)
        
        # 4. Roadmap Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                status TEXT,
                desc TEXT
            )
        """)
        conn.commit()

# ==========================================
# PROFILE OPERATIONS
# ==========================================
def get_startup_profile() -> Dict[str, Any]:
    init_db()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM startup_profile WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else {}

def save_startup_profile(profile: Dict[str, Any]):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE startup_profile
            SET name = ?, idea = ?, target_audience = ?, tech_stack = ?, estimated_budget = ?, currency = ?,
                current_stage = ?, competitor_status = ?, budget_status = ?, roadmap_status = ?, next_task = ?, progress_pct = ?,
                last_updated = ?
            WHERE id = 1
        """, (
            profile.get("name", "Untitled Startup"),
            profile.get("idea", ""),
            profile.get("target_audience", ""),
            profile.get("tech_stack", ""),
            profile.get("estimated_budget", "₹0"),
            profile.get("currency", "INR"),
            profile.get("current_stage", "Ideation"),
            profile.get("competitor_status", "Pending"),
            profile.get("budget_status", "Pending"),
            profile.get("roadmap_status", "Pending"),
            profile.get("next_task", "Introduce your startup idea"),
            profile.get("progress_pct", 10),
            profile.get("last_updated", "Never")
        ))
        conn.commit()

# ==========================================
# CHAT HISTORY OPERATIONS
# ==========================================
def get_chat_history() -> List[Dict[str, str]]:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC")
        rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]

def save_chat_message(role: str, content: str):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
        conn.commit()

# ==========================================
# COMPETITORS OPERATIONS
# ==========================================
def get_competitors() -> List[Dict[str, str]]:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, strength, weakness FROM competitors")
        rows = cursor.fetchall()
        return [{"name": row[0], "strength": row[1], "weakness": row[2]} for row in rows]

def save_competitors(competitors: List[Dict[str, str]]):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM competitors")
        for comp in competitors:
            cursor.execute(
                "INSERT INTO competitors (name, strength, weakness) VALUES (?, ?, ?)",
                (comp.get("name", ""), comp.get("strength", ""), comp.get("weakness", ""))
            )
        conn.commit()

# ==========================================
# ROADMAP OPERATIONS
# ==========================================
def get_roadmap() -> List[Dict[str, str]]:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, status, desc FROM roadmap")
        rows = cursor.fetchall()
        return [{"title": row[0], "status": row[1], "desc": row[2]} for row in rows]

def save_roadmap(roadmap: List[Dict[str, str]]):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM roadmap")
        for mile in roadmap:
            cursor.execute(
                "INSERT INTO roadmap (title, status, desc) VALUES (?, ?, ?)",
                (mile.get("title", ""), mile.get("status", "Pending"), mile.get("desc", ""))
            )
        conn.commit()

# ==========================================
# RESET DATABASE
# ==========================================
def clear_all_memory():
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history")
        cursor.execute("DELETE FROM competitors")
        cursor.execute("DELETE FROM roadmap")
        cursor.execute("""
            UPDATE startup_profile
            SET name = 'Untitled Startup', idea = '', target_audience = '', tech_stack = '', estimated_budget = '₹0', currency = 'INR',
                current_stage = 'Ideation', competitor_status = 'Pending', budget_status = 'Pending', roadmap_status = 'Pending',
                next_task = 'Introduce your startup idea', progress_pct = 10, last_updated = 'Never'
            WHERE id = 1
        """)
        conn.commit()
