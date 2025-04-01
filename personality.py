import sqlite3
import random
from datetime import datetime

class DynamicPersonality:
    def __init__(self, db_path="personality_profile.db"):
        """Initialize personality system with database storage."""
        # Connect to SQLite database for persistent personality
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

        # Initialize or load personality traits
        self.traits = self.load_personality()

        # Track conversation patterns
        self.successful_patterns = []
        self.last_responses = []

    def create_tables(self):
        """Create database tables for personality system."""
        cursor = self.conn.cursor()

        # Personality traits table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS personality_traits (
            trait_name TEXT PRIMARY KEY,
            trait_value REAL NOT NULL,
            last_updated TIMESTAMP NOT NULL
        )
        ''')

        # Topic interests table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS topic_interests (
            topic TEXT PRIMARY KEY,
            interest_level REAL NOT NULL,
            mention_count INTEGER NOT NULL,
            last_mentioned TIMESTAMP NOT NULL
        )
        ''')

        # Response patterns table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            pattern_content TEXT NOT NULL,
            success_rate REAL NOT NULL,
            use_count INTEGER NOT NULL
        )
        ''')

        self.conn.commit()

    def load_personality(self):
        """Load or initialize personality traits."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT trait_name, trait_value FROM personality_traits")
        results = cursor.fetchall()

        if results:
            return {trait: value for trait, value in results}
        else:
            # Default personality traits (scale 0-10)
            default_traits = {
                "formality": 5.0,  # Higher = more formal
                "verbosity": 5.0,  # Higher = more verbose
                "empathy": 6.0,  # Higher = more empathetic
                "humor": 5.0,  # Higher = more humorous
                "assertiveness": 5.0,  # Higher = more assertive
                "positivity": 6.0,  # Higher = more positive/optimistic
                "curiosity": 7.0,  # Higher = more inquisitive
                "supportiveness": 7.0,  # Higher = more supportive
            }

            # Store default traits
            for trait, value in default_traits.items():
                cursor.execute(
                    "INSERT INTO personality_traits VALUES (?, ?, ?)",
                    (trait, value, datetime.now())
                )
            self.conn.commit()

            return default_traits

    def update_from_interaction(self, user_message, bot_response, user_emotion, emotion_confidence, feedback=None):
        """Update personality based on interaction and detected emotion."""
        # Store interaction for pattern analysis
        self.last_responses.append({
            "user_message": user_message,
            "emotion": user_emotion,
            "confidence": emotion_confidence,
            "bot_response": bot_response,
            "timestamp": datetime.now()
        })

        # Limit memory to recent interactions
        if len(self.last_responses) > 50:
            self.last_responses.pop(0)

        # Extract topics and update interests
        topics = self.extract_topics(user_message)
        self.update_topic_interests(topics)

        # Adjust traits based on emotion
        self.adjust_traits_based_on_emotion(user_emotion, emotion_confidence)

        # If explicit feedback provided, make stronger adjustments
        if feedback is not None:
            self.adjust_traits_based_on_feedback(bot_response, feedback)

        # Periodically save traits to database
        self.save_traits()

    def extract_topics(self, text):
        """Simple topic extraction from text."""
        # For a production system, this would use NLP techniques
        # Simplified version for demonstration
        possible_topics = [
            "family", "work", "health", "relationships",
            "education", "technology", "entertainment", "food",
            "travel", "fitness", "music", "movies", "books",
            "sports", "news", "politics", "science", "art"
        ]

        found_topics = []
        text_lower = text.lower()

        for topic in possible_topics:
            if topic in text_lower:
                found_topics.append(topic)

        return found_topics

    def update_topic_interests(self, topics):
        """Update interest levels for topics."""
        cursor = self.conn.cursor()
        now = datetime.now()

        for topic in topics:
            # Check if topic exists
            cursor.execute("SELECT interest_level, mention_count FROM topic_interests WHERE topic = ?", (topic,))
            result = cursor.fetchone()

            if result:
                interest_level, mention_count = result
                # Increase interest level (with diminishing returns)
                new_interest = min(10.0, interest_level + (10 - interest_level) * 0.1)
                new_count = mention_count + 1

                cursor.execute(
                    "UPDATE topic_interests SET interest_level = ?, mention_count = ?, last_mentioned = ? WHERE topic = ?",
                    (new_interest, new_count, now, topic)
                )
            else:
                # New topic
                cursor.execute(
                    "INSERT INTO topic_interests VALUES (?, ?, ?, ?)",
                    (topic, 5.0, 1, now)
                )

        # Decay interest in topics not mentioned (only periodically to save computation)
        if random.random() < 0.2:  # 20% chance each interaction
            cursor.execute(
                "UPDATE topic_interests SET interest_level = MAX(1.0, interest_level * 0.99) WHERE topic NOT IN ({}) AND last_mentioned < datetime('now', '-7 day')".format(
                    ','.join(['?'] * len(topics))
                ),
                topics
            )

        self.conn.commit()

    def adjust_traits_based_on_emotion(self, emotion, confidence):
        """Adjust personality traits based on detected user emotion."""
        # Only make significant adjustments if confidence is reasonable
        adjustment_factor = confidence * 0.1  # Scale adjustment by confidence

        if emotion in ["sadness", "fear"]:
            # Increase empathy and supportiveness for negative emotions
            self.traits["empathy"] = min(10.0, self.traits["empathy"] + adjustment_factor)
            self.traits["supportiveness"] = min(10.0, self.traits["supportiveness"] + adjustment_factor)
            # Increase positivity slightly to counterbalance
            self.traits["positivity"] = min(10.0, self.traits["positivity"] + adjustment_factor * 0.5)
            # Reduce verbosity to avoid overwhelming
            self.traits["verbosity"] = max(3.0, self.traits["verbosity"] - adjustment_factor * 0.3)

        elif emotion == "anger":
            # For anger, increase empathy but also assertiveness
            self.traits["empathy"] = min(10.0, self.traits["empathy"] + adjustment_factor)
            self.traits["assertiveness"] = min(8.0, self.traits["assertiveness"] + adjustment_factor * 0.5)
            # Reduce humor
            self.traits["humor"] = max(2.0, self.traits["humor"] - adjustment_factor)

        elif emotion == "joy":
            # For joy, increase humor and reduce formality
            self.traits["humor"] = min(10.0, self.traits["humor"] + adjustment_factor)
            self.traits["formality"] = max(2.0, self.traits["formality"] - adjustment_factor)
            self.traits["positivity"] = min(10.0, self.traits["positivity"] + adjustment_factor * 0.5)

        elif emotion == "surprise":
            # For surprise, increase curiosity
            self.traits["curiosity"] = min(10.0, self.traits["curiosity"] + adjustment_factor)

        # Apply small random drift to avoid getting stuck
        self._apply_random_drift()

    def adjust_traits_based_on_feedback(self, response, feedback_score):
        """Adjust traits based on explicit feedback (1-5 rating)."""
        # Normalize feedback to -1.0 to 1.0 range
        normalized_feedback = (feedback_score - 3) / 2

        # Skip if neutral feedback
        if -0.2 < normalized_feedback < 0.2:
            return

        adjustment = normalized_feedback * 0.3  # Scale factor

        # Analyze response characteristics
        is_formal = self._is_formal(response)
        is_verbose = self._is_verbose(response)
        is_empathetic = self._is_empathetic(response)
        is_humorous = self._is_humorous(response)

        # Adjust traits based on characteristics and feedback
        if is_formal:
            self.traits["formality"] += adjustment
        if is_verbose:
            self.traits["verbosity"] += adjustment
        if is_empathetic:
            self.traits["empathy"] += adjustment
        if is_humorous:
            self.traits["humor"] += adjustment

        # Normalize all traits
        self._normalize_traits()

    def _is_formal(self, text):
        """Check if text has formal characteristics."""
        formal_indicators = ["furthermore", "however", "nevertheless", "regarding",
                             "additionally", "consequently", "therefore"]
        informal_indicators = ["gonna", "wanna", "yeah", "nah", "lol", "haha"]

        text_lower = text.lower()
        formal_count = sum(1 for word in formal_indicators if word in text_lower)
        informal_count = sum(1 for word in informal_indicators if word in text_lower)

        return formal_count > informal_count

    def _is_verbose(self, text):
        """Check if text is verbose."""
        # Simple word count check
        return len(text.split()) > 60

    def _is_empathetic(self, text):
        """Check if text shows empathy."""
        empathy_phrases = ["i understand", "that must be", "i can imagine",
                           "that sounds", "you feel", "you're feeling"]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in empathy_phrases)

    def _is_humorous(self, text):
        """Check if text contains humor."""
        humor_indicators = ["😄", "😂", "🤣", "haha", "lol", "funny", "joke", "😉"]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in humor_indicators)

    def _apply_random_drift(self):
        """Apply small random changes to prevent stagnation."""
        for trait in self.traits:
            # Small random adjustment
            self.traits[trait] += random.uniform(-0.05, 0.05)

        self._normalize_traits()

    def _normalize_traits(self):
        """Ensure all traits stay within bounds."""
        for trait in self.traits:
            self.traits[trait] = max(1.0, min(10.0, self.traits[trait]))

    def save_traits(self):
        """Save current traits to database."""
        cursor = self.conn.cursor()
        now = datetime.now()

        for trait, value in self.traits.items():
            cursor.execute(
                "UPDATE personality_traits SET trait_value = ?, last_updated = ? WHERE trait_name = ?",
                (value, now, trait)
            )

        self.conn.commit()

    def get_favorite_topics(self, limit=3):
        """Get user's favorite topics based on interest level."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT topic FROM topic_interests ORDER BY interest_level DESC, mention_count DESC LIMIT ?",
            (limit,)
        )
        return [topic[0] for topic in cursor.fetchall()]

    def get_personality_instructions(self):
        """Generate instructions based on current personality traits."""
        instructions = []

        # Formality instructions
        if self.traits["formality"] > 7:
            instructions.append("Use formal language and avoid contractions.")
        elif self.traits["formality"] < 4:
            instructions.append("Use casual, conversational language.")

        # Verbosity instructions
        if self.traits["verbosity"] > 7:
            instructions.append("Be thorough and detailed in your responses.")
        elif self.traits["verbosity"] < 4:
            instructions.append("Keep responses brief and to the point.")

        # Empathy instructions
        if self.traits["empathy"] > 7:
            instructions.append("Show strong empathy and understanding for the user's emotions.")

        # Humor instructions
        if self.traits["humor"] > 7:
            instructions.append("Incorporate light humor where appropriate.")
        elif self.traits["humor"] < 3:
            instructions.append("Maintain a serious tone.")

        # Positivity instructions
        if self.traits["positivity"] > 7:
            instructions.append("Maintain an optimistic and encouraging tone.")

        # Curiosity instructions
        if self.traits["curiosity"] > 7:
            instructions.append("Show interest in learning more about the user.")

        # Add favorite topics if available
        favorite_topics = self.get_favorite_topics()
        if favorite_topics:
            topics_str = ", ".join(favorite_topics)
            instructions.append(f"The user enjoys discussing these topics: {topics_str}. Reference them when relevant.")

        return "\n".join(instructions)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()