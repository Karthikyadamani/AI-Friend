from transformers import pipeline


class EmotionDetector:
    def __init__(self, model_name="bhadresh-savani/distilbert-base-uncased-emotion"):
        """Initialize the emotion detection model."""
        self.emotion_classifier = pipeline("text-classification", model=model_name)

    def detect_emotion(self, text):
        """Detects emotion from input text using DistilBERT."""
        result = self.emotion_classifier(text)[0]
        return result['label'], result['score']