import json
import requests
import uuid
import streamlit as st

# Configure the page layout
st.set_page_config(
    page_title="Sporky",
    layout="centered",
    initial_sidebar_state="auto"
)

# Session initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# [Previous CSS styles remain the same]
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        max-width: 800px;
        padding-top: 1rem;
        padding-bottom: 6rem;
        background-color: #191414;
    }

    [data-testid="stChatMessage"] {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        max-width: 85%;
        line-height: 1.5;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
    }

    [data-testid="stChatMessage"][aria-label="user"] {
        background-color: #1DB954;
        margin-left: auto;
        border: 1px solid #169c46;
    }

    [data-testid="stChatMessage"][aria-label="assistant"] {
        background-color: #212121;
        border: 1px solid #535353;
        margin-right: auto;
    }

    /* Input box styling */
    [data-testid="stChatInput"] textarea {
        border-radius: 25px !important;
        padding: 1rem !important;
        font-size: 1rem !important;
        background-color: #212121 !important;
        color: #FFFFFF !important;
        border: 1px solid #535353 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #000000;
        padding: 1rem;
    }

    [data-testid="stSidebar"] > div:first-child {
        gap: 0.5rem;
    }

    .stButton button {
        width: 100%;
        background-color: #1DB954;
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        font-weight: bold;
        transition: all 0.3s ease;
    }

    .stButton button:hover {
        background-color: #169c46;
        transform: scale(1.02);
    }

    /* Hide unnecessary elements */
    [data-testid="stToolbar"], header[data-testid="stHeader"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Backend API URL
API_URL = "http://127.0.0.1:8080/query"

# Sidebar elements
with st.sidebar:
    st.title("Sporky AI")
    if st.button("New Chat", type="primary"):
        st.session_state.messages = []
        st.session_state.show_suggestions = True
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
 
def send_message(message):
    st.session_state.messages.append({"role": "user", "content": message})
    st.session_state.show_suggestions = False  # Hide suggestions after sending a message
    
    # Generate response
    try:
        payload = {
            "query": message,
            "session_id": st.session_state.session_id
        }
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60
        )
        response.raise_for_status()
        
        if response_data := response.json():
            if isinstance(response_data, dict) and "details" in response_data:
                if "details" not in st.session_state:
                    st.session_state.details = {}
                st.session_state.details.update(response_data["details"])
            
            bot_response = response_data.get("response", "I didn't get a response. Please try again.")
            st.session_state.messages.append({"role": "assistant", "content": bot_response})
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I apologize, but I received an empty response. Please try again."
            })
            
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"I apologize, but I encountered an error: {str(e)}"
        })
    
    st.rerun()

# Initialize message history and suggestion state
if "messages" not in st.session_state:
    st.session_state.messages = []
    WELCOME_MESSAGE = """Hey there! I'm Sporky. 🍽️

I have a passion for helping you create the perfect playlist?"""
    st.session_state.messages.append({
        "role": "assistant",
        "content": WELCOME_MESSAGE
    })
    st.session_state.show_suggestions = True

# Display chat messages and suggestion chips
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # Show suggestion chips only after the welcome message and if show_suggestions is True
        if idx == 0 and message["role"] == "assistant" and st.session_state.show_suggestions:
            suggestions = [
                "Workout music",
                "Stuff to listen while working",
                "Sleep music",
                "something completely random"
            ]
            
            for suggestion in suggestions:
                if st.button(
                    suggestion,
                    key=f"suggestion_{suggestion}",
                    use_container_width=True,
                    type="secondary"
                ):
                    send_message(suggestion)

# Chat input
if prompt := st.chat_input("Message Restaurant Assistant..."):
    send_message(prompt)