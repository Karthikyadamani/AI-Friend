import os
import google.generativeai as genai
from dotenv import load_dotenv
from emotion_detection import EmotionDetector
from personality import DynamicPersonality
from chat_database import ChatDatabase
from sentence_transformers import SentenceTransformer

# Load environment variables from .env file
load_dotenv()


class EmotionChatbot:
    def __init__(self):
        """Initialize the chatbot with enhanced memory and dynamic personality."""
        # Gemini API Configuration from environment variable
        API_KEY = os.getenv('GEMINI_API_KEY')
        if not API_KEY:
            raise ValueError("Missing GEMINI_API_KEY in environment variables")

        genai.configure(api_key=API_KEY)
        self.model = genai.GenerativeModel('models/gemini-1.5-pro-latest')

        # Emotion detection
        self.emotion_detector = EmotionDetector()

        # Initialize services
        self.db = ChatDatabase()
        self.embedding_service = SentenceTransformer("all-MiniLM-L6-v2")

        # Initialize dynamic personality system
        self.personality = DynamicPersonality()

        # Retrieve or create conversation
        self.conversation_id = self.get_or_create_conversation()

        # Track last response for feedback
        self.last_response_id = None

    # Rest of the class remains the same
    def get_or_create_conversation(self, context=None):
        """Retrieve latest conversation or create new one."""
        return self.db.create_conversation(context)

    def detect_emotion(self, text):
        """Detects emotion from input text."""
        return self.emotion_detector.detect_emotion(text)

    def prepare_context(self, user_message, user_emotion):
        """Prepare conversation context with similar past messages and personality."""
        # Find similar past messages
        similar_messages = self.db.find_similar_messages(user_message)

        # Build context string
        context = "Conversation History and Context:\n"
        for msg_role, msg_content, msg_emotion, msg_emotion_confidence in similar_messages:
            context += f"{msg_role} (Emotion: {msg_emotion}): {msg_content}\n"

        # Add personality context
        context += "\n---\nPersonality Instructions:\n"
        context += self.personality.get_personality_instructions()
        context += "\n---\n"

        return context

    def get_gemini_response(self, question, detected_emotion, context):
        """Generates response from Gemini model with personality-infused context."""
        # Create personality-aware prompt
        prompt = f"{context}\n\n"
        prompt += f"The user is feeling {detected_emotion}. "

        # Adjust response instructions based on emotion
        if detected_emotion == "joy":
            prompt += "Match their positive energy while being authentic. "
        elif detected_emotion == "sadness":
            prompt += "Be supportive and empathetic. Acknowledge their feelings. "
        elif detected_emotion == "anger":
            prompt += "Be calm and understanding without being dismissive. "
        elif detected_emotion == "fear":
            prompt += "Be reassuring and provide a sense of safety. "
        elif detected_emotion == "surprise":
            prompt += "Be engaging and responsive to their reaction. "

        # Add personality-specific instructions
        traits = self.personality.traits

        if traits["empathy"] > 7:
            prompt += "Show deep understanding of their perspective. "

        if traits["humor"] > 7:
            prompt += "Use appropriate humor to lighten the mood. "

        if traits["formality"] < 4:
            prompt += "Use casual, friendly language. "
        elif traits["formality"] > 7:
            prompt += "Maintain a more professional tone. "

        if traits["verbosity"] < 4:
            prompt += "Keep your response concise. "
        elif traits["verbosity"] > 7:
            prompt += "Provide a detailed, thoughtful response. "

        prompt += "\n\nUser: " + question + "\nChatbot:"

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"An error occurred: {e}"

    def chat(self, user_input):
        """Main chat method with memory, emotion awareness, and personality adaptation."""
        # Detect emotion
        emotion, confidence = self.detect_emotion(user_input)
        print(f"Detected Emotion: {emotion} (Confidence: {confidence:.2f})")

        # Save user message
        user_message_id = self.db.save_message(
            self.conversation_id,
            "user",
            user_input,
            emotion,
            confidence
        )

        # Prepare context
        context = self.prepare_context(user_input, emotion)

        # Get AI response with personality influence
        response = self.get_gemini_response(user_input, emotion, context)

        # Save AI response
        self.last_response_id = self.db.save_message(
            self.conversation_id,
            "assistant",
            response,
            emotion,
            confidence
        )

        # Update personality based on interaction
        self.personality.update_from_interaction(
            user_input, response, emotion, confidence
        )

        return response

    def provide_feedback(self, feedback_score, feedback_text=None):
        """Allow user to provide feedback on last response."""
        if self.last_response_id:
            # Save feedback in database
            self.db.save_feedback(self.last_response_id, feedback_score, feedback_text)

            # Get the actual response content for personality updating
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT content, emotion, emotion_confidence FROM messages WHERE id = ?",
                           (self.last_response_id,))
            result = cursor.fetchone()

            if result:
                content, emotion, confidence = result
                # Update personality with feedback
                self.personality.update_from_interaction(
                    "", content, emotion, confidence, feedback_score
                )

            return True
        return False

    def close(self):
        """Clean up resources."""
        self.db.close()
        self.personality.close()