import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import speech_to_text
from gtts import gTTS
import webbrowser
import base64
import io

# --- 1. THEME & STYLING ---
st.set_page_config(page_title="Anime AI Assistant", page_icon="⭐")

# Inject Custom CSS for an "App-like" look
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #30363d; }
    .stChatInput { border-radius: 20px; border: 1px solid #58a6ff !important; }
    h1 { color: #58a6ff; font-family: 'Courier New', Courier, monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INITIALIZATION ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["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"]) 


if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. VOICE ENGINE (Anime Tweak) ---
def speak_anime(text):
    if text:
        # We use gTTS but you can change 'lang' or 'tld' for different accents
        tts = gTTS(text=text, lang='en', tld='com.au') # Australian/UK often sounds crisper
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        # The 'playbackRate' makes it sound more energetic like anime!
        md = f"""
            <audio id="audioTag" autoplay>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                var audio = document.getElementById('audioTag');
                audio.playbackRate = 1.25; // Speed up for that energetic anime feel
            </script>
        """
        st.components.v1.html(md, height=0)

# --- 4. COMMANDS ---
def execute_commands(text):
    text = text.lower()
    if "open youtube" in text:
        webbrowser.open("https://www.youtube.com")
        return "Hai! Opening YouTube-chan now! 🌸"
    elif "open spotify" in text:
        webbrowser.open("https://open.spotify.com")
        return "Music time? Yosh! Opening Spotify! 🎵"
    return None

# --- 5. UI LAYOUT ---
st.title("⭐ AI Senpai v2")

# Sidebar for controls
with st.sidebar:
    st.header("Settings")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input Section
voice_input = speech_to_text(language='en', start_prompt="🎤 Speak to me!", stop_prompt="⏹️ Done", key='STT')
chat_input = st.chat_input("Type your message...")
user_query = voice_input if voice_input else chat_input

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    cmd_res = execute_commands(user_query)
    
    with st.chat_message("assistant"):
        if cmd_res:
            st.write(cmd_res)
            speak_anime(cmd_res)
            st.session_state.messages.append({"role": "assistant", "content": cmd_res})
        else:
            # FAST STREAMING LOGIC
            def get_stream():
                stream = client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a cheerful anime character. Use words like 'Sugoi', 'Yosh', and 'Nani' occasionally. Be helpful but energetic!"}] + 
                             [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    stream=True,
                )
                for chunk in stream:
                    yield chunk.choices[0].delta.content or ""

            # st.write_stream is much faster for UI
            full_response = st.write_stream(get_stream())
            speak_anime(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})