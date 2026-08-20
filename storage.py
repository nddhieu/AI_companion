import sys
import sqlite3
import json
import math
import datetime
import uuid
import contextlib
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple

from auth_manager import DEFAULT_USER_ID, DEFAULT_USER_NAME, DEFAULT_DISPLAY_NAME, hash_pin_or_password

if getattr(sys, 'frozen', False):
    DB_PATH = Path(sys.executable).parent / "companion_data.db"
else:
    DB_PATH = Path(__file__).parent / "companion_data.db"

# ---------------- EMBEDDING & VECTOR MATH UTILITIES ---------------- #

def compute_text_embedding(text: str, dimensions: int = 64) -> List[float]:
    """
    Computes a deterministic normalized dense vector embedding for semantic matching.
    Uses character n-grams and hashing with L2-normalization.
    """
    if not text:
        return [0.0] * dimensions

    vec = [0.0] * dimensions
    tokens = re.findall(r"\w+", text.lower())
    
    # Unigrams + Bigrams
    ngrams = list(tokens)
    for i in range(len(tokens) - 1):
        ngrams.append(f"{tokens[i]}_{tokens[i+1]}")
    
    for term in ngrams:
        h = int(hashlib.md5(term.encode("utf-8")).hexdigest(), 16)
        index = h % dimensions
        weight = 1.0 + (len(term) * 0.1)
        vec[index] += weight

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 5) for x in vec]
    return vec

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))

# ---------------- STORAGE MANAGER ---------------- #

class StorageManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextlib.contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _migrate_columns(self, cursor: sqlite3.Cursor, table_name: str, new_columns: Dict[str, str]):
        """Safely adds new columns if they do not exist in existing tables."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing = [row[1] for row in cursor.fetchall()]
        for col_name, col_type in new_columns.items():
            if col_name not in existing:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

    def _init_db(self):
        """Initializes tables for multi-user workspaces, chats, reflection cards, wisdom, knowledge graph, and tasks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                pin_hash TEXT,
                avatar TEXT DEFAULT '🌱',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. Daily Workspaces table (scoped to user_id)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_workspaces (
                user_id TEXT NOT NULL DEFAULT 'default_user',
                date TEXT NOT NULL,
                mood TEXT,
                energy TEXT,
                raw_notes TEXT,
                diary_draft TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, date)
            )
            """)

            # 3. Chat Messages table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                session_date TEXT NOT NULL,
                role TEXT,
                content TEXT,
                mode TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_date ON chat_messages(user_id, session_date)")

            # 4. Reflection Cards table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                date TEXT NOT NULL,
                what_happened TEXT,
                what_i_felt TEXT,
                what_mattered TEXT,
                balanced_perspective TEXT,
                one_small_next_step TEXT,
                what_i_want_to_remember TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_user ON reflection_cards(user_id, date)")

            # 5. Saved Wisdom Library
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_wisdom (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                wisdom_id TEXT,
                title TEXT,
                author_source TEXT,
                topic TEXT,
                concept_summary TEXT,
                user_note TEXT,
                micro_practice TEXT,
                applied INTEGER DEFAULT 0,
                date_saved TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wisdom_user ON saved_wisdom(user_id)")

            # 6. User Profile (Persistent Fact Graph)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source_date TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, key)
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profile_user_cat ON user_profile(user_id, category)")

            # 7. Knowledge Graph Entities (V2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph_entities (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT CHECK(category IN ('person', 'goal', 'stressor', 'value', 'project', 'preference', 'topic')) DEFAULT 'topic',
                emotional_weight REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_ent_user ON knowledge_graph_entities(user_id, category)")

            # 8. Knowledge Graph Relations (V2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph_relations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                last_reinforced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_rel_user ON knowledge_graph_relations(user_id)")

            # 9. Tasks / Next Steps (V2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')) DEFAULT 'pending',
                due_date TEXT,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, status)")

            # 10. Enhanced Episodic Long-Term Memories (V2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                memory_type TEXT DEFAULT 'reflection',
                summary TEXT NOT NULL,
                raw_snippet TEXT,
                emotional_valence TEXT DEFAULT 'Neutral',
                valence_score REAL DEFAULT 0.0,
                arousal_score REAL DEFAULT 0.0,
                importance_score INTEGER DEFAULT 5,
                embedding_json TEXT,
                keywords TEXT,
                superseded_by TEXT,
                is_sensitive INTEGER DEFAULT 0,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            self._migrate_columns(cursor, "episodic_memories", {
                "valence_score": "REAL DEFAULT 0.0",
                "arousal_score": "REAL DEFAULT 0.0",
                "importance_score": "INTEGER DEFAULT 5",
                "embedding_json": "TEXT",
                "superseded_by": "TEXT",
                "is_sensitive": "INTEGER DEFAULT 0",
                "access_count": "INTEGER DEFAULT 0",
                "last_accessed_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            })
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON episodic_memories(user_id, date)")

            # 11. Enhanced Memory Audit & Explainability Log (V2)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                memory_id INTEGER,
                reason TEXT,
                verification_status TEXT DEFAULT 'APPROVED',
                details TEXT,
                signature TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            self._migrate_columns(cursor, "memory_audit_log", {
                "reason": "TEXT",
                "verification_status": "TEXT DEFAULT 'APPROVED'",
                "signature": "TEXT"
            })

            # Seed default user if none exists
            cursor.execute("SELECT COUNT(*) as count FROM users")
            if cursor.fetchone()["count"] == 0:
                cursor.execute(
                    "INSERT INTO users (id, username, display_name, pin_hash, avatar) VALUES (?, ?, ?, ?, ?)",
                    (DEFAULT_USER_ID, DEFAULT_USER_NAME, DEFAULT_DISPLAY_NAME, "", "🌱")
                )

            conn.commit()

        # Clean any historical duplicates on initialization
        try:
            self.cleanup_duplicate_memories()
        except Exception:
            pass

    # ---------------- USER MANAGEMENT ---------------- #

    def get_or_create_user(self, username: str, display_name: Optional[str] = None, pin: Optional[str] = None, avatar: str = "🌱") -> Dict[str, Any]:
        username = username.strip().lower()
        if not display_name:
            display_name = username.capitalize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            user_id = f"u_{uuid.uuid4().hex[:8]}"
            pin_hash = hash_pin_or_password(pin)["hash"] if pin else ""
            cursor.execute(
                "INSERT INTO users (id, username, display_name, pin_hash, avatar) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, display_name, pin_hash, avatar)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return dict(cursor.fetchone())

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, display_name, avatar, created_at, last_active_at FROM users ORDER BY last_active_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def update_user_activity(self, user_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            conn.commit()

    def delete_user(self, user_id: str) -> bool:
        """Cascades deletion across all tables for user_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM daily_workspaces WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM reflection_cards WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM saved_wisdom WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM user_profile WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM knowledge_graph_entities WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM knowledge_graph_relations WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM episodic_memories WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM memory_audit_log WHERE user_id = ?", (user_id,))
            conn.commit()
            return True

    # ---------------- WORKSPACE & CHECK-IN ---------------- #

    def get_or_create_daily_workspace(self, user_id: str = DEFAULT_USER_ID, date_str: Optional[str] = None) -> Dict[str, Any]:
        if not date_str:
            date_str = datetime.date.today().isoformat()
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_workspaces WHERE user_id = ? AND date = ?", (user_id, date_str))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            cursor.execute("""
            INSERT INTO daily_workspaces (user_id, date, mood, energy, raw_notes, diary_draft)
            VALUES (?, ?, '', '', '', '')
            """, (user_id, date_str))
            conn.commit()
            
            cursor.execute("SELECT * FROM daily_workspaces WHERE user_id = ? AND date = ?", (user_id, date_str))
            return dict(cursor.fetchone())

    def update_checkin(self, user_id: str, date_str: str, mood: str, energy: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE daily_workspaces 
            SET mood = ?, energy = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND date = ?
            """, (mood, energy, user_id, date_str))
            conn.commit()
        return self.get_or_create_daily_workspace(user_id, date_str)

    def update_raw_notes(self, user_id: str, date_str: str, raw_notes: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE daily_workspaces 
            SET raw_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND date = ?
            """, (raw_notes, user_id, date_str))
            conn.commit()
        return self.get_or_create_daily_workspace(user_id, date_str)

    def update_diary_draft(self, user_id: str, date_str: str, diary_draft: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE daily_workspaces 
            SET diary_draft = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND date = ?
            """, (diary_draft, user_id, date_str))
            conn.commit()
        return self.get_or_create_daily_workspace(user_id, date_str)

    def get_all_workspaces(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_workspaces WHERE user_id = ? ORDER BY date DESC LIMIT ?", (user_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    # ---------------- CHAT MESSAGES ---------------- #

    def save_chat_message(self, user_id: str, session_date: str, role: str, content: str, mode: str = "Just listen") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO chat_messages (user_id, session_date, role, content, mode)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, session_date, role, content, mode))
            conn.commit()
            return cursor.lastrowid

    def get_chat_history(self, user_id: str, session_date: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM chat_messages 
            WHERE user_id = ? AND session_date = ? 
            ORDER BY timestamp ASC, id ASC
            """, (user_id, session_date))
            return [dict(r) for r in cursor.fetchall()]

    def delete_chat_message(self, user_id: str, message_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE id = ? AND user_id = ?", (message_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    # ---------------- REFLECTION CARDS ---------------- #

    def save_reflection_card(self, user_id: str, card_data: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO reflection_cards (
                user_id, date, what_happened, what_i_felt, what_mattered, 
                balanced_perspective, one_small_next_step, what_i_want_to_remember
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                card_data.get("date", datetime.date.today().isoformat()),
                card_data.get("what_happened", ""),
                card_data.get("what_i_felt", ""),
                card_data.get("what_mattered", ""),
                card_data.get("balanced_perspective", ""),
                card_data.get("one_small_next_step", ""),
                card_data.get("what_i_want_to_remember", "")
            ))
            conn.commit()
            return cursor.lastrowid

    def get_reflection_cards(self, user_id: str, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if date_str:
                cursor.execute("SELECT * FROM reflection_cards WHERE user_id = ? AND date = ? ORDER BY id DESC", (user_id, date_str))
            else:
                cursor.execute("SELECT * FROM reflection_cards WHERE user_id = ? ORDER BY date DESC, id DESC", (user_id,))
            return [dict(r) for r in cursor.fetchall()]

    # ---------------- SAVED WISDOM ---------------- #

    def save_wisdom_item(self, user_id: str, wisdom_data: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO saved_wisdom (
                user_id, wisdom_id, title, author_source, topic, concept_summary, 
                user_note, micro_practice, applied, date_saved
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                wisdom_data.get("wisdom_id", ""),
                wisdom_data.get("title", ""),
                wisdom_data.get("author_source", ""),
                wisdom_data.get("topic", ""),
                wisdom_data.get("concept_summary", ""),
                wisdom_data.get("user_note", ""),
                wisdom_data.get("micro_practice", ""),
                1 if wisdom_data.get("applied") else 0,
                wisdom_data.get("date_saved", datetime.date.today().isoformat())
            ))
            conn.commit()
            return cursor.lastrowid

    def get_saved_wisdom(self, user_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_wisdom WHERE user_id = ? ORDER BY id DESC", (user_id,))
            return [dict(r) for r in cursor.fetchall()]

    def delete_wisdom_item(self, user_id: str, item_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_wisdom WHERE user_id = ? AND id = ?", (user_id, item_id))
            conn.commit()
            return cursor.rowcount > 0

    # ---------------- KNOWLEDGE GRAPH (V2) ---------------- #

    def add_or_update_entity(self, user_id: str, name: str, category: str = "topic", emotional_weight: float = 0.0) -> Dict[str, Any]:
        name_clean = name.strip()
        category_clean = category.strip().lower()
        entity_id = f"ent_{hashlib.md5(f'{user_id}:{name_clean.lower()}'.encode()).hexdigest()[:10]}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO knowledge_graph_entities (id, user_id, name, category, emotional_weight, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                category = excluded.category,
                emotional_weight = excluded.emotional_weight,
                updated_at = CURRENT_TIMESTAMP
            """, (entity_id, user_id, name_clean, category_clean, emotional_weight))
            conn.commit()
            cursor.execute("SELECT * FROM knowledge_graph_entities WHERE id = ?", (entity_id,))
            return dict(cursor.fetchone())

    def get_entities(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute("SELECT * FROM knowledge_graph_entities WHERE user_id = ? AND category = ? ORDER BY name ASC", (user_id, category.lower()))
            else:
                cursor.execute("SELECT * FROM knowledge_graph_entities WHERE user_id = ? ORDER BY category ASC, name ASC", (user_id,))
            return [dict(r) for r in cursor.fetchall()]

    def delete_entity(self, user_id: str, entity_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_graph_entities WHERE user_id = ? AND id = ?", (user_id, entity_id))
            cursor.execute("DELETE FROM knowledge_graph_relations WHERE user_id = ? AND (source_entity_id = ? OR target_entity_id = ?)", (user_id, entity_id, entity_id))
            conn.commit()
            deleted = cursor.rowcount > 0
        if deleted:
            self.log_memory_action(user_id, "user_deleted", None, f"Deleted Knowledge Graph entity ID {entity_id}")
        return deleted

    def add_relation(self, user_id: str, source_name: str, target_name: str, relation_type: str, confidence: float = 1.0) -> Dict[str, Any]:
        source_ent = self.add_or_update_entity(user_id, source_name)
        target_ent = self.add_or_update_entity(user_id, target_name)
        rel_clean = relation_type.strip().upper()
        rel_id = f"rel_{hashlib.md5(f'{user_id}:{source_ent['id']}:{target_ent['id']}:{rel_clean}'.encode()).hexdigest()[:10]}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO knowledge_graph_relations (id, user_id, source_entity_id, target_entity_id, relation_type, confidence, last_reinforced)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                confidence = excluded.confidence,
                last_reinforced = CURRENT_TIMESTAMP
            """, (rel_id, user_id, source_ent["id"], target_ent["id"], rel_clean, confidence))
            conn.commit()
            cursor.execute("SELECT * FROM knowledge_graph_relations WHERE id = ?", (rel_id,))
            return dict(cursor.fetchone())

    def get_knowledge_graph(self, user_id: str) -> Dict[str, Any]:
        entities = self.get_entities(user_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT r.*, s.name as source_name, s.category as source_category, t.name as target_name, t.category as target_category
            FROM knowledge_graph_relations r
            JOIN knowledge_graph_entities s ON r.source_entity_id = s.id
            JOIN knowledge_graph_entities t ON r.target_entity_id = t.id
            WHERE r.user_id = ?
            ORDER BY r.last_reinforced DESC
            """, (user_id,))
            relations = [dict(r) for r in cursor.fetchall()]
        return {"entities": entities, "relations": relations}

    # ---------------- TASKS & ACTION MANAGEMENT (V2) ---------------- #

    def create_task(self, user_id: str, title: str, description: str = "", due_date: Optional[str] = None, category: str = "general") -> Dict[str, Any]:
        task_id = f"tsk_{uuid.uuid4().hex[:8]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO tasks (id, user_id, title, description, status, due_date, category)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (task_id, user_id, title.strip(), description.strip(), due_date, category.strip()))
            conn.commit()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            return dict(cursor.fetchone())

    def get_tasks(self, user_id: str, status: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM tasks WHERE user_id = ?"
            params = [user_id]
            if status:
                sql += " AND status = ?"
                params.append(status)
            if category:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY CASE status WHEN 'pending' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END, created_at DESC"
            cursor.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]

    def update_task_status(self, user_id: str, task_id: str, status: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND id = ?
            """, (status, user_id, task_id))
            conn.commit()
            cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND id = ?", (user_id, task_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_task(self, user_id: str, task_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE user_id = ? AND id = ?", (user_id, task_id))
            conn.commit()
            return cursor.rowcount > 0

    # ---------------- USER PROFILE & FACT GRAPH ---------------- #

    def save_profile_fact(self, user_id: str, category: str, key: str, value: str, confidence: float = 1.0) -> None:
        key = key.strip()
        category = category.strip().lower()
        today_str = datetime.date.today().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO user_profile (user_id, key, category, value, confidence, source_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, key) DO UPDATE SET
                category = excluded.category,
                value = excluded.value,
                confidence = excluded.confidence,
                updated_at = CURRENT_TIMESTAMP
            """, (user_id, key, category, value, confidence, today_str))
            conn.commit()

        self.add_or_update_entity(user_id, name=key, category=category)
        self.log_memory_action(user_id, "extracted", None, f"Saved fact [{category.upper()}] {key}: {value}")

    def get_profile_facts(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute("SELECT * FROM user_profile WHERE user_id = ? AND category = ? ORDER BY updated_at DESC", (user_id, category))
            else:
                cursor.execute("SELECT * FROM user_profile WHERE user_id = ? ORDER BY category ASC, updated_at DESC", (user_id,))
            return [dict(r) for r in cursor.fetchall()]

    def delete_profile_fact(self, user_id: str, key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profile WHERE user_id = ? AND key = ?", (user_id, key))
            conn.commit()
            deleted = cursor.rowcount > 0
        if deleted:
            self.log_memory_action(user_id, "user_deleted", None, f"Deleted fact: {key}")
        return deleted

    # ---------------- ENHANCED EPISODIC MEMORY (V2) ---------------- #

    def cleanup_duplicate_memories(self, user_id: Optional[str] = None) -> int:
        """Removes existing duplicate or near-identical episodic memories, keeping the highest quality entries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("SELECT id, user_id, summary, importance_score, date, embedding_json FROM episodic_memories WHERE user_id = ? AND superseded_by IS NULL ORDER BY id ASC", (user_id,))
            else:
                cursor.execute("SELECT id, user_id, summary, importance_score, date, embedding_json FROM episodic_memories WHERE superseded_by IS NULL ORDER BY id ASC")
            
            all_mems = [dict(r) for r in cursor.fetchall()]
            
            to_delete_ids = []
            seen_by_user: Dict[str, List[Dict[str, Any]]] = {}
            
            for m in all_mems:
                uid = m["user_id"]
                if uid not in seen_by_user:
                    seen_by_user[uid] = []
                
                m_vec = json.loads(m["embedding_json"]) if m.get("embedding_json") else []
                m_sum = " ".join(re.findall(r"\w+", m["summary"].lower()))
                
                is_duplicate = False
                for existing in seen_by_user[uid]:
                    ex_sum = " ".join(re.findall(r"\w+", existing["summary"].lower()))
                    if m_sum == ex_sum:
                        is_duplicate = True
                        break
                    if m_vec and existing.get("vec"):
                        if cosine_similarity(m_vec, existing["vec"]) >= 0.88:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    to_delete_ids.append(m["id"])
                else:
                    seen_by_user[uid].append({"id": m["id"], "summary": m["summary"], "vec": m_vec})

            if to_delete_ids:
                cursor.execute(f"DELETE FROM episodic_memories WHERE id IN ({','.join(['?']*len(to_delete_ids))})", to_delete_ids)
                conn.commit()
            
            return len(to_delete_ids)

    def add_episodic_memory(
        self,
        user_id: str,
        date: str,
        memory_type: str,
        summary: str,
        raw_snippet: str = "",
        emotional_valence: str = "Neutral",
        valence_score: float = 0.0,
        arousal_score: float = 0.0,
        importance_score: int = 5,
        keywords: str = "",
        is_sensitive: bool = False
    ) -> int:
        """Stores atomic episodic memory with dense vector embeddings and 2D affective scores, with automatic deduplication."""
        clean_summary = summary.strip()
        if not clean_summary:
            return 0

        embedding = compute_text_embedding(f"{clean_summary} {raw_snippet} {keywords}")
        embedding_json = json.dumps(embedding)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for existing duplicate / highly similar memories for this user
            cursor.execute("""
                SELECT id, summary, importance_score, embedding_json, date 
                FROM episodic_memories 
                WHERE user_id = ? AND superseded_by IS NULL
                ORDER BY id DESC LIMIT 50
            """, (user_id,))
            recent_memories = cursor.fetchall()
            
            for rm in recent_memories:
                existing_summary = rm["summary"].strip().lower()
                target_summary = clean_summary.lower()
                
                # Check exact text or strong semantic similarity
                exact_match = (existing_summary == target_summary)
                high_similarity = False
                
                if not exact_match and rm["embedding_json"]:
                    try:
                        ex_vec = json.loads(rm["embedding_json"])
                        if cosine_similarity(embedding, ex_vec) >= 0.88:
                            high_similarity = True
                    except Exception:
                        pass
                
                if exact_match or high_similarity:
                    # Update importance score and touch date if newer or higher importance
                    new_importance = max(importance_score, rm["importance_score"])
                    cursor.execute("""
                        UPDATE episodic_memories 
                        SET importance_score = ?, date = ?, access_count = access_count + 1, last_accessed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_importance, date, rm["id"]))
                    conn.commit()
                    self.log_memory_action(user_id, "deduplicated", rm["id"], f"Merged into existing memory: '{clean_summary[:60]}'")
                    return rm["id"]

            cursor.execute("""
            INSERT INTO episodic_memories (
                user_id, date, memory_type, summary, raw_snippet, 
                emotional_valence, valence_score, arousal_score, importance_score,
                embedding_json, keywords, is_sensitive
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, date, memory_type, clean_summary, raw_snippet,
                emotional_valence, valence_score, arousal_score, importance_score,
                embedding_json, keywords, 1 if is_sensitive else 0
            ))
            conn.commit()
            mem_id = cursor.lastrowid

        self.log_memory_action(user_id, "extracted", mem_id, f"Stored memory: '{clean_summary[:60]}' (Importance: {importance_score}/10, Sens: {is_sensitive})")
        return mem_id

    def hybrid_search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_importance: int = 1,
        include_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Multi-Factor Hybrid Ranking with Semantic Diversity Deduplication:
        Score(m) = 0.40 * Sim_dense + 0.25 * Score_lexical + 0.20 * (Importance/10) + 0.15 * Recency_Decay
        """
        query_vec = compute_text_embedding(query)
        query_terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
        today = datetime.date.today()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = """
            SELECT * FROM episodic_memories 
            WHERE user_id = ? AND superseded_by IS NULL AND importance_score >= ?
            """
            params = [user_id, min_importance]
            if not include_sensitive:
                sql += " AND is_sensitive = 0"
            
            cursor.execute(sql, params)
            rows = [dict(r) for r in cursor.fetchall()]

        scored_memories = []
        for r in rows:
            # 1. Dense vector similarity
            mem_vec = json.loads(r["embedding_json"]) if r.get("embedding_json") else []
            sim_dense = cosine_similarity(query_vec, mem_vec)

            # 2. Lexical term match
            lexical_count = sum(1 for term in query_terms if term in r["summary"].lower() or term in (r.get("keywords") or "").lower())
            sim_lexical = min(1.0, lexical_count / max(1, len(query_terms))) if query_terms else 0.5

            # 3. Importance
            importance_weight = max(1, min(10, r.get("importance_score", 5))) / 10.0

            # 4. Recency Decay (half life ~ 60 days, lambda = 0.0115)
            try:
                mem_date = datetime.date.fromisoformat(r["date"])
                days_diff = max(0, (today - mem_date).days)
                recency_decay = math.exp(-0.0115 * days_diff)
            except Exception:
                recency_decay = 0.5

            # Composite Score
            final_score = (0.40 * sim_dense) + (0.25 * sim_lexical) + (0.20 * importance_weight) + (0.15 * recency_decay)
            r["composite_score"] = round(final_score, 4)
            r["sim_dense"] = round(sim_dense, 4)
            scored_memories.append(r)

        scored_memories.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Deduplicate top results to ensure semantic diversity
        deduped_results = []
        seen_summaries = set()
        seen_vectors = []

        for mem in scored_memories:
            norm_summary = " ".join(re.findall(r"\w+", mem["summary"].lower()))
            if not norm_summary or norm_summary in seen_summaries:
                continue

            mem_vec = json.loads(mem["embedding_json"]) if mem.get("embedding_json") else []
            is_dup = False
            if mem_vec:
                for sv in seen_vectors:
                    if cosine_similarity(mem_vec, sv) > 0.82:
                        is_dup = True
                        break
            if is_dup:
                continue

            seen_summaries.add(norm_summary)
            if mem_vec:
                seen_vectors.append(mem_vec)
            deduped_results.append(mem)
            if len(deduped_results) >= limit:
                break

        top_results = deduped_results

        # Update access count & log recall
        if top_results:
            top_ids = [m["id"] for m in top_results]
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE episodic_memories SET access_count = access_count + 1, last_accessed_at = CURRENT_TIMESTAMP WHERE id IN ({','.join(['?']*len(top_ids))})", top_ids)
                conn.commit()

        return top_results

    def search_episodic_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Backward-compatible entry point delegating to hybrid search."""
        return self.hybrid_search_memories(user_id, query=query, limit=limit)

    def get_episodic_memories(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM episodic_memories WHERE user_id = ? AND superseded_by IS NULL ORDER BY date DESC, id DESC LIMIT ?", (user_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    def supersede_memory(self, user_id: str, old_memory_id: int, new_memory_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE episodic_memories SET superseded_by = ? WHERE user_id = ? AND id = ?", (str(new_memory_id), user_id, old_memory_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_episodic_memory(self, user_id: str, memory_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM episodic_memories WHERE user_id = ? AND id = ?", (user_id, memory_id))
            conn.commit()
            deleted = cursor.rowcount > 0
        if deleted:
            self.log_memory_action(user_id, "user_deleted", memory_id, f"Deleted memory ID {memory_id}")
        return deleted

    # ---------------- USER SOVEREIGNTY: FORGET ME PURGE (V2) ---------------- #

    def purge_memories_forget_me(self, user_id: str, target_term: str) -> Dict[str, Any]:
        """
        Cryptographic 'Forget Me' Hard Purge:
        Erases all profile facts, episodic memories, and graph nodes matching target_term.
        Emits a signed cryptographic tombstone in memory_audit_log.
        """
        term_clean = target_term.strip().lower()
        if len(term_clean) < 2:
            return {"status": "error", "message": "Target term too short."}

        deleted_facts = 0
        deleted_memories = 0
        deleted_entities = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Facts
            cursor.execute("DELETE FROM user_profile WHERE user_id = ? AND (LOWER(key) LIKE ? OR LOWER(value) LIKE ?)", (user_id, f"%{term_clean}%", f"%{term_clean}%"))
            deleted_facts = cursor.rowcount

            # 2. Episodic Memories
            cursor.execute("DELETE FROM episodic_memories WHERE user_id = ? AND (LOWER(summary) LIKE ? OR LOWER(raw_snippet) LIKE ? OR LOWER(keywords) LIKE ?)", (user_id, f"%{term_clean}%", f"%{term_clean}%", f"%{term_clean}%"))
            deleted_memories = cursor.rowcount

            # 3. Knowledge Graph
            cursor.execute("SELECT id FROM knowledge_graph_entities WHERE user_id = ? AND LOWER(name) LIKE ?", (user_id, f"%{term_clean}%"))
            ent_ids = [r["id"] for r in cursor.fetchall()]
            if ent_ids:
                cursor.execute(f"DELETE FROM knowledge_graph_relations WHERE user_id = ? AND (source_entity_id IN ({','.join(['?']*len(ent_ids))}) OR target_entity_id IN ({','.join(['?']*len(ent_ids))}))", [user_id] + ent_ids + ent_ids)
                cursor.execute(f"DELETE FROM knowledge_graph_entities WHERE user_id = ? AND id IN ({','.join(['?']*len(ent_ids))})", [user_id] + ent_ids)
                deleted_entities = len(ent_ids)

            conn.commit()

        # Sign cryptographic tombstone
        tombstone_raw = f"{user_id}:{term_clean}:{deleted_facts}:{deleted_memories}:{datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        signature = hashlib.sha256(tombstone_raw.encode("utf-8")).hexdigest()
        
        self.log_memory_action(
            user_id=user_id,
            action="purged_forget_me",
            memory_id=None,
            details=f"Hard purge of '{term_clean}' (Facts: {deleted_facts}, Memories: {deleted_memories}, Graph: {deleted_entities})",
            reason="User exercised Forget Me sovereignty",
            verification_status="PURGED_TOMBSTONE",
            signature=signature
        )

        return {
            "status": "success",
            "term": term_clean,
            "deleted_facts": deleted_facts,
            "deleted_memories": deleted_memories,
            "deleted_entities": deleted_entities,
            "tombstone_signature": signature
        }

    # ---------------- ENHANCED AUDIT & EXPLAINABILITY (V2) ---------------- #

    def log_memory_action(
        self,
        user_id: str,
        action: str,
        memory_id: Optional[int],
        details: str,
        reason: str = "",
        verification_status: str = "APPROVED",
        signature: str = ""
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO memory_audit_log (user_id, action, memory_id, details, reason, verification_status, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, action, memory_id, details, reason, verification_status, signature))
            conn.commit()

    def get_memory_audit_logs(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memory_audit_log WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
            return [dict(r) for r in cursor.fetchall()]

storage = StorageManager()
