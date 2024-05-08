import os
import base64
import gc
import tempfile
import uuid
import requests

from llama_index.core import SimpleDirectoryReader, PromptTemplate

import streamlit as st

# Initialize session state
if "id" not in st.session_state:
    st.session_state.id = uuid.uuid4()
    st.session_state.file_cache = {}

session_id = st.session_state.id

def reset_chat():
    st.session_state.messages = []
    st.session_state.context = None
    gc.collect()

def display_pdf(file):
    st.markdown("### PDF Preview")
    base64_pdf = base64.b64encode(file.read()).decode("utf-8")
    pdf_display = f"""<iframe src="data:application/pdf;base64,{base64_pdf}" width="400" height="100%" type="application/pdf"
                    style="height:100vh; width:100%">
                    </iframe>"""
    st.markdown(pdf_display, unsafe_allow_html=True)

def query_colab_api(prompt, context):
    api_url = "YOUR_COLAB_API_URL"  # Replace with your actual Colab API endpoint
    payload = {"prompt": prompt, "context": context}
    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()["response"]

# Sidebar for file upload
with st.sidebar:
    st.header("Add your documents!")
    uploaded_file = st.file_uploader("Choose your `.pdf` file", type="pdf")

    if uploaded_file:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                file_key = f"{session_id}-{uploaded_file.name}"
                st.write("Indexing your document...")

                if file_key not in st.session_state.get('file_cache', {}):
                    if os.path.exists(temp_dir):
                        loader = SimpleDirectoryReader(input_dir=temp_dir, required_exts=[".pdf"], recursive=True)
                    else:
                        st.error('Could not find the file you uploaded, please check again...')
                        st.stop()
                    
                    docs = loader.load_data()

                    # Save the loaded documents to session state
                    st.session_state.file_cache[file_key] = docs

                st.success("Ready to Chat!")
                display_pdf(uploaded_file)
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.stop()

# Main UI
col1, col2 = st.columns([6, 1])

with col1:
    st.header("Chat with Docs using Llama-3")

with col2:
    st.button("Clear ↺", on_click=reset_chat)

# Initialize chat history
if "messages" not in st.session_state:
    reset_chat()

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What's up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Retrieve documents from session state
        context = st.session_state.file_cache.get(file_key, [])
        # Query the Colab API with the user prompt and document context
        try:
            full_response = query_colab_api(prompt, context)
            message_placeholder.markdown(full_response)
        except Exception as e:
            message_placeholder.markdown(f"Error: {e}")

    st.session_state.messages.append({"role": "assistant", "content": full_response})
