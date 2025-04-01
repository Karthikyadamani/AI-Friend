import sqlite3
from datetime import datetime
from memory_service import EnhancedMemoryService

class ChatDatabase:
    def __init__(self, db_path="emotion_chat_memory.db"):
        """Initialize database with enhanced memory service."""
        # SQLite connection
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

        # Enhanced memory service
        self.memory_service = EnhancedMemoryService()

        # Create tables
        self.create_tables()

    def create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()

        # Conversations table (modified to include conversation_context)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL,
            conversation_context TEXT
        )
        ''')

        # Messages table with additional fields
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            emotion TEXT NOT NULL,
            emotion_confidence REAL NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            is_long_term INTEGER DEFAULT 0,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
        ''')

        # New feedback table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            feedback_score INTEGER,
            feedback_text TEXT,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (message_id) REFERENCES messages (id)
        )
        ''')

        self.conn.commit()

    def create_conversation(self, context=None):
        """Create a new conversation with optional context."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (created_at, conversation_context) VALUES (?, ?)",
            (datetime.now(), context or '')
        )
        self.conn.commit()
        return cursor.lastrowid

    def save_message(self, conversation_id, role, content, emotion, emotion_confidence, is_long_term=False):
        """Save message with option to mark as long-term memory."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, emotion, emotion_confidence, timestamp, is_long_term) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conversation_id, role, content, emotion, emotion_confidence, datetime.now(), int(is_long_term))
        )
        message_id = cursor.lastrowid
        self.conn.commit()

        # Store in vector memory
        self.memory_service.store_message(
            message_id,
            content,
            metadata={
                'role': role,
                'emotion': emotion,
                'emotion_confidence': emotion_confidence,
                'conversation_id': conversation_id
            },
            is_recent=not is_long_term
        )

        return message_id

    def save_feedback(self, message_id, feedback_score, feedback_text=None):
        """Save user feedback for a message."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO message_feedback (message_id, feedback_score, feedback_text, timestamp) VALUES (?, ?, ?, ?)",
            (message_id, feedback_score, feedback_text or '', datetime.now())
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_conversation_context(self, conversation_id):
        """Retrieve conversation context."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT conversation_context FROM conversations WHERE id = ?", (conversation_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def find_similar_messages(self, query_text, include_long_term=True):
        """Find similar messages using enhanced memory service."""
        # Retrieve similar messages
        similar_messages = self.memory_service.retrieve_similar_messages(
            query_text,
            include_long_term=include_long_term
        )

        # Convert to expected format
        return [
            (
                message_meta.get('role', 'unknown'),
                doc,
                message_meta.get('emotion', 'neutral'),
                message_meta.get('emotion_confidence', 0.0)
            )
            for doc, message_meta in similar_messages
        ]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()