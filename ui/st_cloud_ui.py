import os
import streamlit as st
import requests
import time
import uuid
# pyrefly: ignore [missing-import]
import logfire


# Initialize Logfire
try:
    logfire.configure(token=st.secrets.get("LOGFIRE_TOKEN", os.getenv("LOGFIRE_TOKEN")))
    logfire.instrument_requests()   # propagates trace context to the FastAPI backend
    LOGFIRE_STATUS = "Connected & Tracing"
except Exception:
    LOGFIRE_STATUS = "Standby (No Token)"

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Welyft Assistant",
    page_icon="🚚",
    layout="wide",
)

# --- AVATARS ---
AI_AVATAR = "🚚"
USER_AVATAR = "👤"

# --- BRAND ACCENT ---
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

    base_url = "http://localhost:8000"

    st.markdown("---")
    st.success(f"Logfire: {LOGFIRE_STATUS}")
    st.info(f"Memory ID: {st.session_state.session_id[:8]}")

    if st.button("🗑️ Clear History & Memory", width="stretch", type="primary"):
        logfire.warning(f"🗑️ Memory Wipe Triggered for session: {st.session_state.session_id}")
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
            data = {}
            with st.status("🔍 Welyft Assistant is thinking...", expanded=True) as status:
                try:
                    with logfire.span("📡 Calling RAG Backend"):
                        url = f"{base_url}/query"
                        payload = {"q": prompt, "thread_id": st.session_state.session_id}
                        response = requests.post(url, json=payload, timeout=60)

                        if response.status_code != 200:
                            st.error(f"Backend Error: {response.status_code} - {response.text}")
                            st.stop()

                        data = response.json()

                    steps = data.get("thought_process", [])
                    for step in steps:
                        st.markdown(f"⚙️ {step}", unsafe_allow_html=False)

                    status.update(label="✅ Answer Synthesized", state="complete", expanded=False)

                except Exception as e:
                    logfire.error(f"❌ UI-Backend Connection Failed: {e}")
                    status.update(label="❌ Connection Failed", state="error")
                    st.error("Backend Offline.")
                    st.stop()

            # Answer streaming — outside status so it's always visible
            answer_placeholder = st.empty()
            full_answer = data.get("answer", "No response.")

            curr_text = ""
            for char in full_answer:
                curr_text += char
                answer_placeholder.markdown(curr_text + "▌")
                time.sleep(0.005)
            answer_placeholder.markdown(full_answer)

            # Sources — outside status so they're visible after it collapses
            sources = data.get("sources", [])
            if sources:
                with st.expander(f"📄 Retrieved Context ({len(sources)} chunks)"):
                    for i, source in enumerate(sources):
                        st.caption(f"Chunk {i + 1}")
                        st.info(source)
            else:
                st.caption("ℹ️ No context retrieved — conversational response.")

            st.session_state.messages.append({"role": "assistant", "content": full_answer})
            logfire.info("✅ Chat cycle completed successfully.")