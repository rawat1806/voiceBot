import streamlit as st
import speech_recognition as sr
import requests
import os
import time

FASTAPI_BACKEND_URL = "http://localhost:8000"
UPLOAD_DIR = "./"
os.makedirs(UPLOAD_DIR, exist_ok=True)
user_role = "user"
assistant_role = "assistant"
failure_message = "Sorry, I couldn't understand you. Please try again."

st.title("Voice Chatbot Demo")

# Create a placeholder for messages
message_placeholder = st.empty()

# initialize the chat history 
if "messages" not in st.session_state:
    st.session_state.messages = []
    # messages = [{"role": "user", "text": "Hi"}, {..}];

# Display chat messages from history on app 
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

# Function to display a message in the chat
def show_in_chat(role, text):
    with st.chat_message(role):
        st.write(text)
    st.session_state.messages.append({"role": role, "text": text})

def show_audio_response():
    # print("showing audio response")
    with st.chat_message(assistant_role):
        st.audio("voice.mp3")
    

# Function to display a message and wait before replacing it
def display_message(msg, message_type="info"):
    if message_type == "success":
        message_placeholder.success(msg)
    elif message_type == "error":
        message_placeholder.error(msg)
    elif message_type == "warning":
        message_placeholder.warning(msg)
    else:
        message_placeholder.info(msg)

def save_audio_file(audio_file):
    file_path = os.path.join(UPLOAD_DIR, "user")
    with open(file_path, "wb") as f:
        f.write(audio_file.getbuffer())
    display_message("Audio file uploaded successfully.", message_type="success")
    return file_path


def text_to_text_response(input_text):
    assistant_reply = None
    response = requests.post(FASTAPI_BACKEND_URL + "/chat", json={"input": input_text})
    if response.status_code != 200:
        display_message("Failed to get a valid response from the LLM.", message_type="error")
    else:
        data = response.json()
        assistant_reply = data["text"]
        show_in_chat(assistant_role, assistant_reply)
    return assistant_reply

def voice_to_text_response(file_path, audio_file):
    reply = None
    with open(file_path, 'rb') as f:
        files = {'file': (audio_file.name, f, audio_file.type)}
        response = requests.post(FASTAPI_BACKEND_URL + "/transcribe", files=files)
    # Display the result from the backend
    if response.status_code == 200:
        data = response.json()
        reply = data["text"]["text"]
        show_in_chat(user_role, reply)
    else:
        display_message("Failed to transcribe the audio file.", message_type="error")
    return reply 

def text_to_voice_response(text):
    audioFileName = None
    response = requests.post(FASTAPI_BACKEND_URL + "/audio", json={"input": text})
    if response.status_code != 200:
        display_message("Failed to generate voice response.", message_type="error")
        return audioFileName
    else:
        with open("voice.mp3", "wb") as f:
            f.write(response.content)
        display_message("Voice response generated successfully.", message_type="success")
        audioFileName = "voice.mp3"
        return audioFileName

    
def llm_conversation(file_path, audio_file):
    reply = voice_to_text_response(file_path, audio_file)
    if reply is None: 
        show_in_chat(assistant_role, failure_message)
    else:
        display_message("Transcribed successfully.", message_type="success")

        #generating response 
        assistant_reply = text_to_text_response(reply)
        # print(assistant_reply)
        if assistant_reply is None:
            show_in_chat(assistant_role, failure_message)
        else:
            display_message("LLM response generated successfully.", message_type="success")
            time.sleep(1)
            #generating audio file
            display_message("Generating audio output", message_type="info")
            audioFileName = text_to_voice_response(assistant_reply)
            if audioFileName is not None:
                show_audio_response()
            else:
                show_in_chat(assistant_role, failure_message)


def main():
    st.sidebar.title("Configuration")

    audio_file = st.sidebar.file_uploader("Upload an audio",
     type=["mp3"],
      accept_multiple_files=False)

    if audio_file is None:
        display_message("Please upload an audio file.", message_type="warning")
        return
    
    if audio_file is not None:
        file_path = save_audio_file(audio_file) #save the audio file
        if st.sidebar.button("Send"):
            try:
                llm_conversation(file_path, audio_file)  #send the audio file to backend
            except Exception as e:
                st.sidebar.error(f"Error while sending audio: {e}")


if __name__ == "__main__":
    main()