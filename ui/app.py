import os
import streamlit as st
import requests
import time
import uuid
# pyrefly: ignore [missing-import]
import logfire
from dotenv import load_dotenv


# Load environment variables explicitly from the root directory
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)


# Initialize Logfire
try:
    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        print("ERROR: LOGFIRE_TOKEN is empty or None!")
    logfire.configure(token=token)
    # logfire.instrument_requests() # Disabled due to OpenTelemetry bug on Windows: MeterProvider.get_meter() got multiple values for argument 'version'
    LOGFIRE_STATUS = "Connected & Tracing"
except Exception as e:
    print(f"Logfire Init Error in UI: {e}")
    LOGFIRE_STATUS = f"Standby (Error: {e})"



# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Welyft Assistant",
    page_icon="🚚",
    layout="wide",
)

# --- AVATARS ---
AI_AVATAR = "🚚"
USER_AVATAR = "👤"

# --- BRAND ACCENT (Streamlit theme covers most widgets automatically via
# .streamlit/config.toml, this just tightens a couple of details theme
# alone doesn't reach — chat bubble backgrounds and the status/expander border) ---
st.markdown("""
<style>
    div[data-testid="stChatMessage"] {
        border-radius: 12px;
        border: 1px solid #2a2a2a;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #2a2a2a;
        border-radius: 10px;
    }
    button[kind="primary"] {
        color: #111111 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


# --- FAQ CATEGORIES (instant answers — no backend / LLM call) ---
FAQ_CATEGORIES = {
    "About Welyft": [
        ("What is Welyft?",
         "Welyft is a Singapore-based logistics company operating a 100% "
         "electric van fleet, providing last-mile and mid-mile delivery for "
         "both businesses and everyday consumers, with sustainability built "
         "into the core of its service."),
        ("Who founded Welyft?",
         "Welyft is led by CEO Pramod Jain and COO Nimisha Jain, and is "
         "backed by Wejain, a private equity firm, along with other "
         "investors focused on sustainable logistics."),
        ("How is Welyft different from other delivery services?",
         "Welyft's entire delivery fleet is 100% electric, giving businesses "
         "auditable, low-carbon delivery data for ESG and Scope 3 reporting "
         "— delivery with a measurable sustainability story, not just speed."),
    ],
    "Sustainability": [
        ("Why does Welyft use electric vehicles?",
         "Welyft's fleet cuts CO2 emissions by about 52% compared to diesel "
         "vans, supports Singapore's Green Plan 2030, and reduces noise "
         "pollution, while giving business clients verifiable "
         "emissions-reduction data."),
        ("How does Welyft support Singapore's Green Plan 2030?",
         "Welyft's operations are aligned with Singapore's Green Plan 2030, "
         "which mandates phasing out petrol and diesel vehicles by 2040."),
    ],
    "Services": [
        ("What kind of deliveries can Welyft handle?",
         "Welyft supports individual parcel and courier deliveries as well "
         "as enterprise bulk shipments, dedicated fleet contracts, and "
         "recurring business logistics, across last-mile and mid-mile "
         "routes island-wide."),
        ("Which industries does Welyft work with?",
         "Welyft serves enterprise clients across FMCG, electronics, "
         "pharmaceuticals, and healthcare, alongside everyday individual "
         "consumers."),
        ("Does Welyft deliver across all of Singapore?",
         "Yes, Welyft operates island-wide across Singapore, offering both "
         "on-demand and scheduled deliveries."),
    ],
    "Business enquiries": [
        ("How can my business book deliveries with Welyft?",
         "Businesses can reach out to the Welyft team directly to discuss "
         "delivery volume, fleet needs, and pricing — contact details are "
         "available on welyft.org."),
        ("Can I set up a dedicated fleet contract?",
         "Yes, Welyft offers dedicated fleet arrangements for businesses "
         "with recurring or high-volume delivery needs — reach out via the "
         "website to discuss your requirements."),
    ],
    "Careers": [
        ("Is Welyft hiring drivers right now?",
         "Welyft is actively growing its electric fleet and team as it "
         "expands — check the careers section on welyft.org for current "
         "openings, since these change as the company scales."),
        ("What's it like to drive for Welyft?",
         "Welyft frames its driver partners as part of its sustainability "
         "mission, driving electric vehicles as part of a green fleet. For "
         "specific pay and terms, check current openings on the site."),
    ],
    "Policies": [
        ("What is Welyft's cancellation or refund policy?",
         "I don't have the specific policy terms on hand — please check "
         "Welyft's terms of service on the website or contact the team "
         "directly for exact details."),
        ("What payment methods does Welyft accept?",
         "For the most current payment options, please check directly with "
         "the Welyft team or the booking page, so I don't give you outdated "
         "information."),
    ],
    "Contact": [
        ("How do I get in touch with Welyft?",
         "You can reach out through welyft.org for general enquiries. For "
         "media and press specifically, contact details are listed in "
         "Welyft's press materials."),
    ],
}


# --- SESSION MANAGEMENT ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logfire.info(f"✨ New User Session Created: {st.session_state.session_id}")

if "messages" not in st.session_state:
    st.session_state.messages = []


# --- SIDEBAR ---
with st.sidebar:
    st.title("🚚 Welyft")
    st.caption("Business · Personal · Peer-to-peer delivery, answered instantly")
    st.markdown("---")
    st.success(f"Logfire: {LOGFIRE_STATUS}")
    st.info(f"Memory ID: {st.session_state.session_id[:8]}")

    if st.button("🗑️ Clear History & Memory", width="stretch", type="primary"):
        logfire.warn(f"🗑️ Memory Wipe Triggered for session: {st.session_state.session_id}")
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# --- MAIN CHAT ---
st.title("🚚 Welyft Assistant")
st.caption("Ask about business shipping, personal deliveries, or sending items to friends & family.")

# --- FAQ SUGGESTED QUESTIONS ---
st.markdown("##### 💡 Frequently Asked Questions")
for category, qa_pairs in FAQ_CATEGORIES.items():
    with st.expander(category):
        for question, answer in qa_pairs:
            if st.button(question, key=f"{category}-{question}"):
                st.session_state.messages.append({"role": "user", "content": question})
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.rerun()

with st.expander("Other"):
    st.caption("Ask anything not covered above — this goes to the full AI assistant.")

st.markdown("---")

# Display history
for message in st.session_state.messages:
    avatar = AI_AVATAR if message["role"] == "assistant" else USER_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask Welyft anything about delivery..."):
    # START TRACE: User Interaction
    with logfire.span("💬 User Chat Interaction", user_query=prompt, session_id=st.session_state.session_id):

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        # Assistant Response
        with st.chat_message("assistant", avatar=AI_AVATAR):
            with st.status("🔍 Welyft Assistant is thinking...", expanded=True) as status:
                try:
                    # DISTRIBUTED TRACE: Calling Backend
                    with logfire.span("📡 Calling RAG Backend"):
                        # Get backend URL from env, or default to local if not set
                        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                        url = f"{base_url}/query"
                        payload = {"q": prompt, "thread_id": st.session_state.session_id}
                        response = requests.post(url, json=payload, timeout=60)
                        data = response.json()

                    # Show Reasoning Steps from Backend
                    steps = data.get("thought_process", [])
                    for step in steps:
                        st.write(f"⚙️ {step}")

                    status.update(label="✅ Answer Synthesized", state="complete", expanded=False)

                    # --- SHOW SOURCES (NESTED EXPANDABLES) ---
                    sources = data.get("sources", [])
                    if sources:
                        with st.expander("📄 View Retrieved Context (Sources)"):
                            for i, source in enumerate(sources):
                                # Create a preview title for each chunk
                                preview = source[:100].replace("\n", " ") + "..."
                                with st.expander(f"Chunk {i+1}: {preview}"):
                                    st.info(source)
                except Exception as e:
                    logfire.error(f"❌ UI-Backend Connection Failed: {e}")
                    status.update(label="❌ Connection Failed", state="error")
                    st.error("Backend Offline.")
                    st.stop()

            # Final Answer Streaming
            answer_placeholder = st.empty()
            full_answer = data.get("answer", "No response.")

            curr_text = ""
            for char in full_answer:
                curr_text += char
                answer_placeholder.markdown(curr_text + "▌")
                time.sleep(0.005)

            answer_placeholder.markdown(full_answer)
            st.session_state.messages.append({"role": "assistant", "content": full_answer})
            logfire.info("✅ Chat cycle completed successfully.")