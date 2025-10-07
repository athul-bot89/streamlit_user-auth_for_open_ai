import streamlit as st
import msal
import os
from openai import AzureOpenAI

# ===========================
# CONFIGURATION
# ===========================
CLIENT_ID = os.getenv("CLIENT_ID")  
TENANT_ID = os.getenv("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_PATH = "/redirect"
SCOPE = ["https://cognitiveservices.azure.com/.default"]
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = f"https://yoyo-midhun-e4apfthfc2f9c0d8.southindia-01.azurewebsites.net{REDIRECT_PATH}"

def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache,
    )

# ===========================
# INITIALIZE SESSION STATE
# ===========================
if "token" not in st.session_state:
    st.session_state.token = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(page_title="Azure AI Chat", page_icon="💬", layout="wide")

# ===========================
# AUTHENTICATION
# ===========================
if not st.session_state.token:
    st.title("🔐 Azure AI Chat Application")
    st.markdown("### Please login to continue")
    
    msal_app = build_msal_app()
    query_params = st.query_params

    if "code" in query_params:
        code = query_params["code"]
        result = msal_app.acquire_token_by_authorization_code(
            code,
            scopes=SCOPE,
            redirect_uri=REDIRECT_URI,
        )
        if "access_token" in result:
            st.session_state.token = result
            st.rerun()
        else:
            st.error(f"❌ Login failed: {result.get('error_description')}")
    else:
        auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.markdown(f"### [🔑 Login via Microsoft]({auth_url})")
        st.info("Click the link above to authenticate with your Microsoft account")

# ===========================
# CHAT APPLICATION
# ===========================
else:
    # Header with logout button
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("💬 Azure AI Chat")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.token = None
            st.session_state.messages = []
            st.rerun()

    # Initialize Azure OpenAI client
    token_provider = lambda: st.session_state.token["access_token"]
    endpoint = os.getenv("ENDPOINT_URL", "https://ai-kokuljosetesthub385023345165.openai.azure.com/")
    #endpoint = os.getenv("ENDPOINT_URL", "https://az-openai-botangelos.openai.azure.com/")
    deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1-mini")
    #deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini")
    
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2025-01-01-preview",
    )

    # Sidebar for chat controls
    with st.sidebar:
        st.header("⚙️ Chat Settings")
        
        temperature = st.slider("Temperature", 0.0, 2.0, 1.0, 0.1)
        max_tokens = st.slider("Max Tokens", 100, 4000, 1000, 100)
        
        st.divider()
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        st.caption(f"Model: {deployment}")
        st.caption(f"Messages: {len(st.session_state.messages)}")

    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            try:
                # Prepare messages for API
                api_messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant."
                    }
                ]
                
                # Add conversation history
                for msg in st.session_state.messages:
                    api_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

                # Call Azure OpenAI API
                with st.spinner("Thinking..."):
                    completion = client.chat.completions.create(
                        model=deployment,
                        messages=api_messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=0.95,
                        frequency_penalty=0,
                        presence_penalty=0,
                        stop=None,
                        stream=False
                    )

                # Extract and display response
                assistant_message = completion.choices[0].message.content
                message_placeholder.markdown(assistant_message)
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
