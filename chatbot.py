import streamlit as st
import os
import streamlit as st
import base64
import io
import webbrowser
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import requests
import streamlit.components.v1 as components

LIVE2D_HTML = """
<!DOCTYPE html>
<html>
<head>
    <!-- Cubism Core for Cubism 3/4 -->
    <script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
    <!-- Cubism Core for Cubism 2.1 (Needed for Shizuku and earlier VTuber models) -->
    <script src="https://cdn.jsdelivr.net/gh/dylanNew/live2d/webgl/Live2D/lib/live2d.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@6.5.2/dist/browser/pixi.min.js"></script>
    <!-- Use index.min.js for broad version support -->
    <script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display/dist/index.min.js"></script>
    <style>
        body { margin: 0; overflow: hidden; background-color: transparent; }
        #loading { position: absolute; color: white; padding: 20px; font-family: sans-serif; text-align: center; width: 100%; top: 40%;}
        canvas { display: block; border-radius: 15px; position: relative; z-index: 10;}
    </style>
</head>
<body>
    <div id="loading">✨ Waking up Kimi...</div>
    <canvas id="canvas"></canvas>
    <script>
        const app = new PIXI.Application({
            view: document.getElementById('canvas'),
            autoStart: true,
            transparent: true,
            backgroundAlpha: 0,
            width: 300,
            height: 400
        });

        // Use the exactly requested Mao model from the official samples
        const modelUrl = "https://cdn.jsdelivr.net/gh/Live2D/CubismWebSamples@develop/Samples/Resources/Mao/Mao.model3.json";
        
        PIXI.live2d.Live2DModel.from(modelUrl).then(model => {
            document.getElementById('loading').style.display = 'none';
            app.stage.addChild(model);
            
            // Smart auto-scaling so any model fits nicely
            const scaleX = app.renderer.width / model.width;
            const scaleY = app.renderer.height / model.height;
            model.scale.set(Math.min(scaleX, scaleY) * 0.8); 
            
            model.x = app.renderer.width / 2;
            model.y = app.renderer.height / 2 + (model.height * model.scale.y * 0.1);
            model.anchor.set(0.5, 0.5);

            app.view.addEventListener('pointermove', (e) => {
                model.focus(e.clientX, e.clientY);
            });

            if ("{react_state}" === "talk") {
                model.motion("Tap", 0);
            }
        }).catch(err => {
            document.getElementById('loading').innerText = "Oops! Anime model failed to load :(";
        });
    </script>
</body>
</html>
"""

def render_avatar(state="idle"):
    html_code = LIVE2D_HTML.replace("{react_state}", state)
    components.html(html_code, height=400)

# Configure Groq API
client = OpenAI(
    api_key=st.secrets["GROQ"]["API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

LANGUAGES = {
    "English": {
        "voiceId": "en-US-samantha",
        "whisker_lang": "en",
        "system_prompt": "You are a helpful, friendly, and extremely cute AI assistant. Speak strictly in English. Use cute expressions, friendly conversational tone, and fun emojis. Answer concisely but cheerfully!"
    },
    "Hindi": {
        "voiceId": "hi-IN-ayushi",
        "whisker_lang": "hi",
        "system_prompt": "You are a helpful, friendly, and extremely cute AI assistant. Speak strictly in Hindi (Devanagari script). Use cute expressions, friendly conversational tone, and fun emojis. Answer concisely but cheerfully!"
    },
    "Japanese": {
        "voiceId": "ja-JP-kimi",
        "whisker_lang": "ja",
        "system_prompt": "You are a helpful, friendly, and extremely cute AI assistant. Speak strictly in Japanese. Use cute anime-style expressions, friendly conversational tone, and fun emojis. Answer concisely but cheerfully!"
    }
}

if "language" not in st.session_state:
    st.session_state.language = "Hindi"

# --- 1. THEME & STYLING ---
st.set_page_config(page_title="Kimi AI Assistant", page_icon="🎀", layout="wide", initial_sidebar_state="expanded")

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

theme_css = ""
if st.session_state.theme == "Dark":
    theme_css = """
    .stApp { background: radial-gradient(circle at bottom right, #2a1b38, #161224); }
    .stChatMessage { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); }
    .stChatInputContainer { background: rgba(255,255,255,0.05) !important; border: 1px solid #ff7eb3 !important; }
    h1 { color: #ff7eb3; text-shadow: 0 0 15px rgba(255,126,179,0.5); }
    div[data-testid="stSidebar"] { background: rgba(20, 15, 30, 0.6) !important; border-right: 1px solid rgba(255,255,255,0.05); }
    p, span, div, label { color: #ffffff !important; }
    svg { fill: #ffffff !important; stroke: #ffffff !important; }
    """
else:
    theme_css = """
    .stApp { background: radial-gradient(circle at bottom right, #fff0f5, #ffe6fa); }
    .stChatMessage { background: rgba(255, 255, 255, 0.6); border: 1px solid rgba(0, 0, 0, 0.05); }
    .stChatInputContainer { background: rgba(255,255,255,0.9) !important; border: 1px solid #ff3385 !important; }
    h1 { color: #ff3385; text-shadow: 0 0 15px rgba(255,126,179,0.3); }
    div[data-testid="stSidebar"] { background: rgba(255, 240, 245, 0.8) !important; border-right: 1px solid rgba(0,0,0,0.05); }
    p, span, div, label { color: #333333 !important; }
    svg { fill: #333333 !important; stroke: #333333 !important; }
    """

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Nunito', sans-serif !important;
    }}
    .stChatMessage {{
        backdrop-filter: blur(12px);
        border-radius: 20px;
        margin-bottom: 15px;
        padding: 5px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }}
    .stChatInputContainer {{
        border-radius: 30px;
        box-shadow: 0 0 15px rgba(255,126,179,0.2);
    }}
    h1 {{ font-weight: 700; }}
    div[data-testid="stSidebar"] {{ backdrop-filter: blur(15px); }}
    img {{ border-radius: 15px; }}
    
    {theme_css}
    </style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2. VOICE ENGINE ---
def speak(text):
    if text:
        try:
            url = "https://api.murf.ai/v1/speech/generate"
            headers = {
                "api-key": st.secrets["MURF"]["API_KEY"],
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            data = {
                "voiceId": LANGUAGES[st.session_state.language]["voiceId"],
                "style": "Conversational",
                "text": text,
                "modelId": "FALCON"
            }
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                audio_url = response.json().get('audioFile')
                md = f"""
                    <audio id="audioTag" autoplay>
                        <source src="{audio_url}" type="audio/mp3">
                    </audio>
                    <script>
                        var audio = document.getElementById('audioTag');
                        audio.playbackRate = 1.0;
                    </script>
                """
                st.components.v1.html(md, height=0)
                return audio_url
            else:
                st.error(f"Murf AI API Error: {response.text}")
        except Exception as e:
            st.error(f"Error speaking: {e}")
    return ""

# --- 3. COMMANDS ---
def execute_commands(text):
    text = text.lower()
    if "open youtube" in text:
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube for you!"
    elif "open spotify" in text:
        webbrowser.open("https://open.spotify.com")
        return "Opening Spotify for you!"
    return None

# --- 4. UI LAYOUT ---
st.title("🎀 Kimi AI Assistant")

with st.sidebar:
    st.markdown("### ✨ Kimi Avatar")
    anime_placeholder = st.empty()
    with anime_placeholder:
        render_avatar("idle")

    st.header("Settings")
    
    # Language toggle
    lang_list = list(LANGUAGES.keys())
    selected_lang = st.selectbox("Language", lang_list, index=lang_list.index(st.session_state.language))
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()

    # Theme toggle
    selected_theme = st.radio("Appearance", ["Dark", "Light"], horizontal=True, index=0 if st.session_state.theme == "Dark" else 1)
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.rerun()
        
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("### Microphone")
    audio_info = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop Recording", key='recorder')

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.write(msg["content"])
        elif isinstance(msg["content"], list):
            text_only = " ".join([c["text"] for c in msg["content"] if c.get("type") == "text"])
            st.write(text_only)

chat_input = st.chat_input("Type your message...")

# Trigger processing if the user spoke or typed
user_query = None

if audio_info and 'bytes' in audio_info:
    try:
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language=LANGUAGES[st.session_state.language]["whisker_lang"]
        )
        user_query = transcription.text
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")

if chat_input:
    user_query = chat_input

if user_query:
    model_name = "llama-3.3-70b-versatile"

    # Display user input in UI
    with st.chat_message("user"):
        st.write(user_query)

    # Convert to standard format for Groq API
    st.session_state.messages.append({"role": "user", "content": user_query})

    cmd_res = execute_commands(user_query)
    
    with st.chat_message("assistant"):
        if cmd_res:
            st.write(cmd_res)
            
            speak(cmd_res)
            with anime_placeholder:
                render_avatar("talk")
                
            st.session_state.messages.append({"role": "assistant", "content": cmd_res})
        else:
            try:
                # Prepare payload for Groq API
                api_messages = [
                    {"role": "system", "content": LANGUAGES[st.session_state.language]["system_prompt"]}
                ]
                
                # Append history
                for m in st.session_state.messages:
                    if isinstance(m["content"], str):
                        api_messages.append({"role": m["role"], "content": m["content"]})
                    elif isinstance(m["content"], list):
                        text_only = " ".join([c["text"] for c in m["content"] if c.get("type") == "text"])
                        api_messages.append({"role": m["role"], "content": text_only})
                
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=api_messages,
                    stream=True,
                )
                
                def get_stream():
                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                
                full_response = st.write_stream(get_stream())
                
                speak(full_response)
                with anime_placeholder:
                    render_avatar("talk")
                        
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error communicating with Groq API: {e}")
