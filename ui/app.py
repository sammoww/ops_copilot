"""Streamlit chat interface for OpsCopilot SRE incident response."""

import json
import os
import httpx
import streamlit as st

API_URL = os.getenv("OPSCOPILOT_API_URL", "http://localhost:8000")

st.set_page_config(page_title="OpsCopilot", page_icon="🚨", layout="centered")
st.title("🚨 OpsCopilot SRE Assistant")
st.caption("Grounded DevOps & SRE Incident Response with Live Telemetry and Action Tools")

# Initialize multi-turn chat history in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Hello! I am OpsCopilot. Ask me about service status, operational runbooks, or filing incident tickets."}
    ]

# Render existing chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User chat input
if prompt := st.chat_input("Ask an operational question (e.g., 'Is auth-service down?')..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response via FastAPI SSE endpoint
    with st.chat_message("assistant"):
        def generate_stream():
            try:
                with httpx.Client(timeout=30.0) as client:
                    with client.stream("POST", f"{API_URL}/api/v1/chat/stream", json={"message": prompt}) as response:
                        if response.status_code != 200:
                            yield f"⚠️ API Error ({response.status_code}): Unable to stream response."
                            return
                        for line in response.iter_lines():
                            if line.startswith("data: ") and not line.endswith("[DONE]"):
                                data = json.loads(line[6:])
                                if "token" in data:
                                    yield data["token"]
            except Exception as e:
                yield f"⚠️ Connection error: Could not reach OpsCopilot API at {API_URL}. Details: {str(e)}"

        full_response = st.write_stream(generate_stream())
        st.session_state["messages"].append({"role": "assistant", "content": full_response})
