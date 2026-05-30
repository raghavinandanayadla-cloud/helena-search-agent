import os
import asyncio
import nest_asyncio
import streamlit as st

nest_asyncio.apply()

os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search
from google.genai import types

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
)

@st.cache_resource
def get_runner():
    agent = Agent(
        name="Helen",
        model=Gemini(
            model="gemini-2.5-flash",
            retry_options=retry_config
        ),
        description="A simple agent that can answer general questions.",
        instruction="You are a helpful assistant. Use Google Search for current info or if unsure.",
        tools=[google_search],
    )
    runner = InMemoryRunner(agent=agent)
    # Create the session once when runner is initialized
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="user",
            session_id="session"
        )
    )
    return runner

async def get_response(runner, prompt):
    reply_parts = []
    new_message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)]
    )
    async for event in runner.run_async(
        user_id="user",
        session_id="session",
        new_message=new_message
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    reply_parts.append(part.text)
    return "".join(reply_parts) if reply_parts else "No response received."

st.set_page_config(
    page_title="Helen · ADK Agent",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Helen")
st.caption("Powered by Google ADK · Gemini 2.5 Flash")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm Helen. Ask me anything — I can search the web for current info too."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask Helen anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Helen is thinking..."):
            try:
                runner = get_runner()
                loop = asyncio.get_event_loop()
                reply = loop.run_until_complete(get_response(runner, prompt))
            except Exception as e:
                reply = f"⚠️ Error: {e}"

        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("**Model:** gemini-2.5-flash")
    st.info("**Tools:** Google Search")
    st.metric("Messages", len(st.session_state.messages))

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat cleared! How can I help you?"}
        ]
        st.rerun()
