from chatbot import EmotionChatbot

def main():
    chatbot = EmotionChatbot()
    print("Enhanced AI Friend Chatbot with Dynamic Personality started.")
    print("Type 'quit', 'exit', or 'bye' to end.")
    print("Type 'feedback <1-5>' to provide feedback on the last response.")

    while True:
        user_input = input("You: ")

        # Check for feedback command
        if user_input.lower().startswith('feedback '):
            try:
                # Extract score (and optional text)
                parts = user_input[9:].split(' ', 1)
                score = int(parts[0])
                text = parts[1] if len(parts) > 1 else None

                if 1 <= score <= 5:
                    if chatbot.provide_feedback(score, text):
                        print(f"Thanks for your feedback! (Score: {score}/5)")
                    else:
                        print("No recent response to provide feedback for.")
                else:
                    print("Please provide a score between 1 and 5.")
            except (ValueError, IndexError):
                print("Invalid feedback format. Use 'feedback <1-5> [optional comment]'")
            continue

        # Check for exit command
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Chatbot: It was nice talking with you! Goodbye!")
            chatbot.close()
            break

        # Normal chat flow
        response = chatbot.chat(user_input)
        print("Chatbot:", response)
        print("(You can provide feedback with 'feedback <1-5>')")

if __name__ == "__main__":
    main()
