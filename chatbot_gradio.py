import gradio as gr
import requests
from gtts import gTTS
import io
import speech_recognition as sr
import tempfile
import os

API_KEY = "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"

blocked_keywords = [
    "politics", "political", "election", "government", "president",
    "religion", "religious", "christian", "muslim", "bible", "quran", "god"
]

def contains_blocked_keywords(text):
    return any(word in text.lower() for word in blocked_keywords)

def chat(user_message, history):
    # history is a list of dicts: [{"role": "user", "content": ...}, ...]
    if contains_blocked_keywords(user_message):
        bot_reply = "❌ That topic is not allowed."
        history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": bot_reply}
        ]
        return history, history
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://your-project.com",
        "Content-Type": "application/json"
    }
    # Build conversation history for the API
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ] + history + [{"role": "user", "content": user_message}]
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": messages
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        reply = response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        reply = f"⚠️ Error: {e}"
    history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply}
    ]
    return history, history

def history_to_chatbot_pairs(history):
    # Convert list of dicts to list of [user, bot] pairs
    pairs = []
    user_msg = None
    for msg in history:
        if msg["role"] == "user":
            user_msg = msg["content"]
        elif msg["role"] == "assistant" and user_msg is not None:
            pairs.append([user_msg, msg["content"]])
            user_msg = None
    return pairs

def history_to_markdown(history):
    md = ""
    for msg in history:
        if msg["role"] == "user":
            md += f"**You:** {msg['content']}\n\n"
        elif msg["role"] == "assistant":
            md += f"**Bot:** {msg['content']}\n\n"
    return md if md else "No conversation yet."

def transcribe_audio(audio_path):
    if audio_path is None:
        return ""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)  # type: ignore
    except Exception as e:
        text = f"⚠️ Could not transcribe: {e}"
    return text

def text_to_speech(text):
    tts = gTTS(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.write_to_fp(fp)
        temp_path = fp.name
    return temp_path

def save_conversation_to_file(history, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        for msg in history:
            if msg["role"] == "user":
                f.write(f"You: {msg['content']}\n\n")
            elif msg["role"] == "assistant":
                f.write(f"Bot: {msg['content']}\n\n")

with gr.Blocks() as demo:
    gr.Markdown("# 🤖 OpenRouter Chatbot\nA simple chatbot using OpenRouter API. Forbidden topics are filtered.")
    state = gr.State([])  # chat history as list of dicts
    with gr.Tabs():
        with gr.TabItem("Chat"):
            chatbot = gr.Chatbot(label="Chat")
            with gr.Row():
                user_input = gr.Textbox(label="Your Message", lines=2)
                send_btn = gr.Button("Send")
            audio_input = gr.Audio(type="filepath", label="Upload Audio for Speech-to-Text")
            transcribe_btn = gr.Button("Transcribe Audio")
            tts_audio = gr.Audio(label="Bot Speech", interactive=False)
            tts_btn = gr.Button("🔊 Speak Bot Reply")
            def respond(user_message, history):
                new_history, _ = chat(user_message, history)
                # Save the updated conversation to file
                save_conversation_to_file(
                    new_history,
                    r"C:\Ricafrente\Natural Language Processing\Chatbot\generated_transcription.txt"
                )
                return history_to_chatbot_pairs(new_history), new_history
            send_btn.click(respond, inputs=[user_input, state], outputs=[chatbot, state])
            send_btn.click(lambda x, y: "", [user_input, state], user_input)  # clear input after send
            user_input.submit(respond, inputs=[user_input, state], outputs=[chatbot, state])
            user_input.submit(lambda x, y: "", [user_input, state], user_input)
            # When transcribe button is clicked, transcribe audio and set textbox
            def handle_transcribe(audio):
                return transcribe_audio(audio)
            transcribe_btn.click(handle_transcribe, inputs=audio_input, outputs=user_input)
            # When TTS button is clicked, speak the last bot reply
            def handle_tts(history):
                # Find last bot message
                for msg in reversed(history):
                    if msg["role"] == "assistant":
                        return text_to_speech(msg["content"])
                return None
            tts_btn.click(handle_tts, inputs=state, outputs=tts_audio)
        with gr.TabItem("History"):
            history_md = gr.Markdown(value="No conversation yet.", label="Chat History")
            def update_history(history):
                return history_to_markdown(history)
            demo.load(lambda history: history_to_markdown(history), state, history_md)
            send_btn.click(update_history, state, history_md)
            user_input.submit(update_history, state, history_md)

demo.launch() 