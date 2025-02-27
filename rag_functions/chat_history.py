import os
import json
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# Get directory to store session histories
current_directory = os.path.dirname(os.path.abspath(__file__))
history_dir = os.path.join(current_directory, "sessions")
os.makedirs(history_dir, exist_ok=True)

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id in store:
        return store[session_id]

    history_file = os.path.join(history_dir, f"{session_id}.json")
    history = ChatMessageHistory()

    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                messages = json.load(f)
                for msg in messages:
                    if msg.get("role") == "human":
                        history.add_user_message(msg.get("content", ""))
                    elif msg.get("role") == "ai":
                        history.add_ai_message(msg.get("content", ""))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading session {session_id}: {e}")

    store[session_id] = history
    return history

def save_session_history(session_id: str):
    if session_id not in store:
        return

    history = store[session_id]
    messages = [
        {"role": "human", "content": msg.content} if isinstance(msg, HumanMessage)
        else {"role": "ai", "content": msg.content}
        for msg in history.messages
    ]

    history_file = os.path.join(history_dir, f"{session_id}.json")

    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2)
    except IOError as e:
        print(f"Error saving session {session_id}: {e}")
