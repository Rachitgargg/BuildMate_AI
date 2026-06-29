import streamlit as st
import time
import os
import json
import urllib.parse
import base64
from dotenv import load_dotenv
from agent.agent import generate_co_founder_response
import memory.sqlite_memory as db

# Load environment variables
load_dotenv(override=True)

# Initialize SQLite Database
db.init_db()

# Load and encode logo to base64
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        return ""

logo_base64 = get_image_base64("assets/logo.png")
if logo_base64:
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0 0 4px rgba(6,182,212,0.3));" />'
else:
    logo_html = '⚡'

def format_currency(value, currency="INR"):
    if not value or value == "Pending":
        return "Pending"
    try:
        if isinstance(value, str):
            value = value.replace("₹", "").replace("$", "").replace(",", "").strip()
            if not value or value == "Pending":
                return "Pending"
            if "." in value:
                value = value.split(".")[0]
            value = float(value)
        if currency == "USD" or currency == "$":
            return f"${int(value):,}"
        else:
            # INR
            s = str(int(value))
            if len(s) <= 3:
                return "₹" + s
            last_three = s[-3:]
            other_parts = s[:-3]
            res = []
            while len(other_parts) > 0:
                res.append(other_parts[-2:])
                other_parts = other_parts[:-2]
            res.reverse()
            return "₹" + ",".join(res) + "," + last_three
    except Exception:
        return str(value)

def generate_personalized_recommendations(profile, competitors, roadmap):
    idea = profile.get("idea", "")
    stage = profile.get("current_stage", "Ideation")
    budget = profile.get("estimated_budget", "Pending")
    comp_count = len(competitors)
    
    high_tasks = []
    med_tasks = []
    low_tasks = []
    
    if not idea or idea == "":
        high_tasks.append("Define your core startup idea and value proposition in the chat.")
        med_tasks.append("Identify your target audience and user persona.")
        low_tasks.append("Brainstorm potential names for your startup.")
    else:
        if comp_count == 0:
            high_tasks.append("Perform market research in the chat to identify and map direct competitors.")
        else:
            high_tasks.append(f"Analyze the strengths and weaknesses of the {comp_count} identified competitors.")
            
        if budget == "Pending" or budget in ["$0", "₹0"]:
            high_tasks.append("Use the MVP Budget Estimator to calculate a localized development cost.")
        else:
            med_tasks.append(f"Optimize your MVP scope to fit within the {budget} budget limit.")
            
        if not roadmap:
            med_tasks.append("Generate your 30-day roadmap and milestone strategy with the co-founder.")
        else:
            high_tasks.append("Refine Phase 1 milestones on your roadmap to prepare for launch.")
            
        tech_stack = profile.get("tech_stack", "")
        if not tech_stack or tech_stack == "Not specified yet.":
            med_tasks.append("Select and document your core technology stack based on MVP requirements.")
        else:
            low_tasks.append(f"Evaluate developer availability and licensing for {tech_stack}.")
            
        if stage == "Ideation":
            med_tasks.append("Conduct 5 user interviews to validate the core problem.")
            low_tasks.append("Create a simple landing page to collect early sign-ups.")
        elif stage == "Validation":
            high_tasks.append("Set up a landing page with a waitlist to measure conversion rate.")
            med_tasks.append("Draft wireframes for the core user flow.")
        elif stage == "MVP Planning":
            high_tasks.append("Finalize the Product Requirement Document (PRD) for your MVP.")
            med_tasks.append("Create a database schema design.")
            
    if not high_tasks:
        high_tasks.append("Review your roadmap milestones and mark completed tasks.")
    if not med_tasks:
        med_tasks.append("Prepare a pitch deck outline for early-stage investors.")
    if not low_tasks:
        low_tasks.append("Set up domain name and social media handles.")
        
    return high_tasks, med_tasks, low_tasks

# ==========================================
# QUERY PARAMETERS & ACTION HANDLING
# ==========================================
# Handle "New session" or "Clear memory" action
if st.query_params.get("action") in ["new_session", "clear_memory"]:
    db.clear_all_memory()
    st.session_state.messages = []
    st.session_state.active_tab = "chat"
    st.query_params.clear()
    st.toast("🗑️ Console memory cleared!", icon="⚠️")
    st.rerun()

# Initialize active tab in session state
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"

# Initialize session start time & interaction tracking
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
if "last_interaction_time" not in st.session_state:
    from datetime import datetime
    st.session_state.last_interaction_time = datetime.now().strftime("%I:%M %p")

# Handle Tab navigation from query params
if "tab" in st.query_params:
    st.session_state.active_tab = st.query_params["tab"]

# ==========================================
# PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="BuildMate AI - Your AI Startup Co-Founder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Custom CSS for the Futuristic SaaS Aesthetic
st.markdown("""
<style>
    /* Import Space Grotesk, Outfit, and Tabler Icons Webfont */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Outfit:wght@300;400;600;800&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css');
    
    /* Global Background with Grid Texture and Typography */
    .stApp {
        background-color: #020d1a;
        background-image: 
            linear-gradient(rgba(6, 182, 212, 0.04) 1px, transparent 1px), 
            linear-gradient(90deg, rgba(6, 182, 212, 0.04) 1px, transparent 1px);
        background-size: 32px 32px;
        font-family: 'Space Grotesk', 'Outfit', sans-serif;
        color: #bfdbfe;
    }

    /* Remove default Streamlit top padding and margins */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
    }

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    /* Global Glow Orbs */
    .global-glow {
        position: fixed;
        pointer-events: none;
        filter: blur(100px);
        z-index: 0;
    }
    .glow-tr {
        top: -50px;
        right: -50px;
        width: 260px;
        height: 260px;
        background: radial-gradient(circle, rgba(6,182,212,0.13), transparent 70%);
    }
    .glow-bl {
        bottom: -50px;
        left: -50px;
        width: 220px;
        height: 220px;
        background: radial-gradient(circle, rgba(59,130,246,0.09), transparent 70%);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(6, 182, 212, 0.04) !important;
        border-right: 1px solid rgba(6, 182, 212, 0.1) !important;
        height: 100vh !important;
        overflow-y: auto !important;
    }

    /* Eliminate empty space at the top of the sidebar */
    div[data-testid="stSidebarHeader"] {
        display: none !important;
    }
    div[data-testid="stSidebarContent"] {
        padding-top: 0px !important;
    }

    [data-testid="stSidebarUserContent"] {
        display: flex !important;
        flex-direction: column !important;
        min-height: 100vh !important;
        padding-top: 0px !important;
        padding-bottom: 1rem !important;
        gap: 0.6rem !important;
    }

    [data-testid="stSidebarUserContent"] > div:last-child {
        margin-top: auto !important;
        padding-bottom: 0px !important;
    }

    /* Transparent Streamlit Header */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        background: transparent !important;
    }

    /* Clear Console Memory Button */
    .btn-clear-memory {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.2);
        color: #f87171 !important;
        border-radius: 9px;
        font-size: 12.5px;
        padding: 8px 12px;
        text-decoration: none !important;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    .btn-clear-memory:hover {
        background: rgba(239,68,68,0.15);
        border-color: rgba(239,68,68,0.35);
        box-shadow: 0 0 10px rgba(239,68,68,0.1);
    }

    /* Quick Actions Button */
    .quick-action-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 8px 12px;
        border-radius: 9px;
        background: rgba(6,182,212,0.06);
        border: 1px solid rgba(6,182,212,0.1);
        color: #67e8f9 !important;
        font-size: 12.5px;
        text-decoration: none !important;
        transition: all 0.2s ease;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .quick-action-btn:hover {
        background: rgba(6,182,212,0.15);
        border-color: rgba(6,182,212,0.25);
        box-shadow: 0 0 10px rgba(6,182,212,0.1);
    }

    /* Header Container & Glow Orbs */
    .header-container {
        position: relative;
        background: rgba(2, 13, 26, 0.6) !important;
        border: 1px solid rgba(6, 182, 212, 0.12) !important;
        border-radius: 16px;
        padding: 1.8rem 2.5rem;
        margin-bottom: 2rem;
        overflow: hidden;
    }
    
    .glow-orb {
        position: absolute;
        width: 300px;
        height: 300px;
        pointer-events: none;
        filter: blur(80px);
        opacity: 0.15;
    }
    
    .glow-cyan {
        top: -150px;
        right: -150px;
        background: radial-gradient(circle, #06b6d4, transparent 70%);
    }
    
    .glow-blue {
        bottom: -150px;
        left: -150px;
        background: radial-gradient(circle, #3b82f6, transparent 70%);
    }
    
    .header-content {
        position: relative;
        z-index: 1;
    }

    .header-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .header-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, #fff 20%, #67e8f9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .header-subtitle {
        font-size: 1rem;
        font-weight: 400;
        color: #4b6a7a;
        margin-top: 0.25rem;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    /* New Session / Export Button */
    .btn-new-session {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(6, 182, 212, 0.07);
        border: 1px solid rgba(6, 182, 212, 0.2);
        border-radius: 8px;
        color: #67e8f9 !important;
        padding: 0.4rem 0.8rem;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none !important;
        transition: all 0.2s ease;
    }
    .btn-new-session:hover {
        background: rgba(6, 182, 212, 0.15);
        border-color: rgba(6, 182, 212, 0.35);
        box-shadow: 0 0 10px rgba(6, 182, 212, 0.15);
    }

    @keyframes borderPulse {
        0% { border-color: rgba(6, 182, 212, 0.2); }
        50% { border-color: rgba(6, 182, 212, 0.5); box-shadow: 0 0 8px rgba(6, 182, 212, 0.15); }
        100% { border-color: rgba(6, 182, 212, 0.2); }
    }
    /* Pulsing AI Status Badge */
    .status-badge {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(6, 182, 212, 0.08);
        border: 1px solid rgba(6, 182, 212, 0.2);
        color: #22d3ee;
        padding: 0.4rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
        animation: borderPulse 2s infinite;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #06b6d4;
        border-radius: 50%;
        box-shadow: 0 0 8px #22d3ee;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(6, 182, 212, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(6, 182, 212, 0); }
    }

    /* Stats Strip */
    .stats-strip {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-top: 1.5rem;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stat-card {
        position: relative;
        background: rgba(6, 182, 212, 0.05);
        border: 1px solid rgba(6, 182, 212, 0.1);
        border-radius: 10px;
        padding: 9px 12px;
        transition: all 0.2s ease;
        overflow: hidden;
        animation: fadeIn 0.4s ease-out;
    }
    
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, #0284c7, #06b6d4);
        opacity: 0;
        transition: opacity 0.25s ease;
    }
    
    .stat-card:hover::before {
        opacity: 1;
    }
    
    .stat-card:hover {
        border-color: rgba(6, 182, 212, 0.25);
        background: rgba(6, 182, 212, 0.08);
    }
    
    .stat-label {
        font-size: 0.75rem;
        color: #4b6a7a;
        display: flex;
        align-items: center;
        gap: 0.35rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #22d3ee;
        margin: 0.2rem 0;
    }
    
    .stat-delta {
        font-size: 0.75rem;
        color: #06b6d4;
        display: flex;
        align-items: center;
        gap: 0.2rem;
    }
    
    .stat-delta-down {
        font-size: 0.75rem;
        color: #3b82f6;
        display: flex;
        align-items: center;
        gap: 0.2rem;
    }

    /* Tabs Under Header */
    .tabs-container {
        display: flex;
        border-bottom: 1px solid rgba(6, 182, 212, 0.08);
        margin-top: 1.5rem;
        gap: 2rem;
        padding-bottom: 0px;
        position: relative;
        z-index: 1;
    }
    
    .tab-item {
        padding: 10px 5px;
        text-decoration: none !important;
        color: #6b8ea0 !important;
        font-weight: 500;
        font-size: 0.95rem;
        border-bottom: 2px solid transparent;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .tab-item:hover {
        color: #a5f3fc !important;
    }
    
    .tab-item.active {
        border-bottom: 2px solid #06b6d4 !important;
        color: #22d3ee !important;
    }

    /* Section Headings */
    .section-heading {
        font-size: 20px;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #fff, #67e8f9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Style Streamlit Chat Messages to match the Futuristic SaaS Aesthetic */
    .stChatMessage {
        background-color: rgba(6, 182, 212, 0.04) !important;
        border: 1px solid rgba(6, 182, 212, 0.1) !important;
        margin-bottom: 1rem !important;
        padding: 1rem !important;
    }
    
    /* AI Chat Message (Assistant) */
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        margin-right: auto !important;
        max-width: 80% !important;
        border-left: 2px solid #06b6d4 !important;
        border-radius: 0 10px 10px 10px !important;
    }
    
    /* User Chat Message */
    .stChatMessage[data-testid="stChatMessageUser"] {
        margin-left: auto !important;
        max-width: 80% !important;
        border-right: 2px solid #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.04) !important;
        border-color: rgba(59, 130, 246, 0.1) !important;
        border-radius: 10px 0 10px 10px !important;
        color: #bfdbfe !important;
    }

    /* Typing Indicator */
    .typing-indicator {
        display: flex;
        gap: 6px;
        padding: 0.75rem 1rem;
        align-self: flex-start;
        background: rgba(6, 182, 212, 0.06);
        border: 1px solid rgba(6, 182, 212, 0.12);
        border-radius: 0 10px 10px 10px;
        border-left: 2px solid #06b6d4;
        width: fit-content;
    }

    .typing-dot {
        width: 6px;
        height: 6px;
        background: #06b6d4;
        border-radius: 50%;
        animation: blink 1.4s infinite both;
    }

    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes blink {
        0% { opacity: .2; }
        20% { opacity: 1; }
        100% { opacity: .2; }
    }

    /* Custom Chat Input */
    div[data-testid="stChatInput"] {
        border-top: 1px solid rgba(6, 182, 212, 0.08) !important;
        background-color: rgba(2, 12, 26, 0.6) !important;
        border-radius: 12px !important;
        padding: 10px !important;
    }

    div[data-testid="stChatInput"] textarea {
        color: #bfdbfe !important;
    }
    
    div[data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #0284c7, #06b6d4) !important;
        border-radius: 9px !important;
        color: white !important;
    }

    /* Sidebar Profile Completeness Progress Bar */
    .profile-progress-container {
        margin-top: 1.5rem;
        padding: 0 0.5rem;
    }

    .profile-progress-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        margin-bottom: 0.4rem;
    }

    .profile-progress-label {
        color: #4b6a7a;
    }

    .profile-progress-val {
        color: #22d3ee;
        font-weight: 700;
    }

    .profile-progress-track {
        background: rgba(255, 255, 255, 0.06);
        height: 4px;
        border-radius: 99px;
        overflow: hidden;
    }

    .profile-progress-fill {
        background: linear-gradient(90deg, #0284c7, #06b6d4);
        height: 100%;
        border-radius: 99px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* User Profile Row Footer */
    .user-profile-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: rgba(6, 182, 212, 0.05);
        border: 1px solid rgba(6, 182, 212, 0.08);
        border-radius: 9px;
        padding: 7px 8px;
        margin-top: 1.5rem;
    }
    
    .user-avatar {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background: rgba(6, 182, 212, 0.15);
        border: 1px solid rgba(6, 182, 212, 0.25);
        border-radius: 50%;
        color: #22d3ee;
        font-weight: 700;
        font-size: 0.85rem;
    }
    
    .user-info {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .user-name {
        font-size: 0.85rem;
        font-weight: 600;
        color: #bfdbfe;
        line-height: 1.2;
    }
    
    .user-plan {
        font-size: 0.7rem;
        color: #4b6a7a;
        font-weight: 500;
    }
    
    .settings-icon {
        margin-left: auto;
        color: #4b6a7a;
        font-size: 1.1rem;
        cursor: pointer;
        transition: color 0.2s ease;
    }
    .settings-icon:hover {
        color: #22d3ee;
    }

    /* Muted Text */
    .muted-text {
        color: #4b6a7a;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD STATE FROM SQLITE MEMORY
# ==========================================
startup_profile = db.get_startup_profile()
competitors = db.get_competitors()
roadmap = db.get_roadmap()
chat_history = db.get_chat_history()

# Initialize session state from DB if empty
if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = chat_history if chat_history else [
        {"role": "assistant", "content": "Hello! I am your AI Startup Co-Founder. Tell me about your startup idea, and we can begin validating it, performing market research, and estimating your MVP development costs."}
    ]

if not chat_history:
    db.save_chat_message("assistant", st.session_state.messages[0]["content"])

# Initialize active tab in session state
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"

# Calculate Profile Completeness (20% per filled field)
completeness_pct = 0
if startup_profile.get("name") and startup_profile.get("name") != "Untitled Startup":
    completeness_pct += 20
if startup_profile.get("idea"):
    completeness_pct += 20
if startup_profile.get("target_audience"):
    completeness_pct += 20
if startup_profile.get("tech_stack"):
    completeness_pct += 20
if startup_profile.get("estimated_budget") and startup_profile.get("estimated_budget") not in ["$0", "₹0", "0", "", None]:
    completeness_pct += 20

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
user_messages_count = sum(1 for msg in st.session_state.messages if msg["role"] == "user")
formatted_budget = format_currency(startup_profile.get("estimated_budget", "₹0"), startup_profile.get("currency", "INR"))

with st.sidebar:
    # Compact Inline Brand Row with Logo
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0.5rem; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(6, 182, 212, 0.1); padding-bottom: 1rem;">
        <div style="width: 44px; height: 44px; background: linear-gradient(135deg, rgba(6,182,212,0.2), rgba(59,130,246,0.15)); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 4px; box-shadow: 0 0 15px rgba(6, 182, 212, 0.1);">{logo_html}</div>
        <div style="display: flex; flex-direction: column;">
            <span style="font-weight: 800; font-size: 1.2rem; color: #fff; line-height: 1.2;">BuildMate AI</span>
            <span style="font-size: 0.72rem; color: #4b6a7a; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.15rem;">Accelerator Console</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Global Controls
    st.markdown("""
    <div style="padding: 0 0.5rem; margin-bottom: 0.8rem;">
        <div class="profile-progress-label" style="margin-bottom: 0.4rem;">Console Controls</div>
        <a href="/?action=clear_memory" target="_self" class="btn-clear-memory">
            <i class="ti ti-trash"></i> Clear Console Memory
        </a>
    </div>
    """, unsafe_allow_html=True)
        
    # Profile Completeness Progress Bar
    st.markdown(f"""
    <div class="profile-progress-container" style="margin-bottom: 0.8rem;">
        <div class="profile-progress-header">
            <span class="profile-progress-label">Console Completeness</span>
            <span class="profile-progress-val">{completeness_pct}%</span>
        </div>
        <div class="profile-progress-track">
            <div class="profile-progress-fill" style="width: {completeness_pct}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Display Current Memory State
    st.markdown(f"""
    <div style="padding: 10px 12px; background: rgba(6, 182, 212, 0.03); border: 1px solid rgba(6, 182, 212, 0.08); border-radius: 9px; margin-bottom: 0.8rem;">
        <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #2d5a6e; margin-bottom: 8px; letter-spacing: 0.05em;"><i class="ti ti-database"></i> Memory State</div>
        <div style="font-size: 0.8rem; line-height: 1.8; color: #8fa0b5;">
            <i class="ti ti-rocket" style="color: #22d3ee; font-size: 13px; margin-right: 6px;"></i><strong>Startup:</strong> {startup_profile.get("name", "Untitled Startup")}<br>
            <i class="ti ti-calendar" style="color: #22d3ee; font-size: 13px; margin-right: 6px;"></i><strong>Stage:</strong> {startup_profile.get("current_stage", "Ideation")}<br>
            <i class="ti ti-coin" style="color: #22d3ee; font-size: 13px; margin-right: 6px;"></i><strong>Budget:</strong> {formatted_budget}<br>
            <i class="ti ti-search" style="color: #22d3ee; font-size: 13px; margin-right: 6px;"></i><strong>Competitors Found:</strong> {len(competitors)} mapped<br>
            <i class="ti ti-map" style="color: #22d3ee; font-size: 13px; margin-right: 6px;"></i><strong>Roadmap Status:</strong> {startup_profile.get("roadmap_status", "Pending")}<br>
            <i class="ti ti-clock" style="color: #22d3ee; font-size: 13px; margin-right: 6px;"></i><strong>Last Updated:</strong> {startup_profile.get("last_updated", "Never")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Session Info Section
    st.markdown(f"""
    <div style="padding: 0 0.5rem; margin-bottom: 0.8rem;">
        <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #2d6070; margin-bottom: 8px; letter-spacing: 0.05em;">Current Session</div>
        <div style="background: rgba(6, 182, 212, 0.04); border: 1px solid rgba(6, 182, 212, 0.08); border-radius: 10px; padding: 10px 12px; font-size: 0.8rem; color: #8fa0b5; line-height: 1.6;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span>Interactions</span>
                <span style="color: #22d3ee; font-weight: 600;">{user_messages_count}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span>Last interaction</span>
                <span style="color: #22d3ee; font-weight: 600;">{st.session_state.last_interaction_time}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>Status</span>
                <span style="color: #22d3ee; font-weight: 600; display: flex; align-items: center; gap: 4px;"><span class="status-dot" style="width: 6px; height: 6px; box-shadow: 0 0 4px #22d3ee;"></span>Active</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # User Profile Row (placed inside a div that will be pushed to bottom via CSS)
    st.markdown("""
    <div class="sidebar-footer" style="width: 100%;">
        <div class="user-profile-row" style="margin-top: 0;">
            <div class="user-avatar">R</div>
            <div class="user-info">
                <span class="user-name">Rachit</span>
                <span class="user-plan">Premium Founder</span>
            </div>
            <i class="ti ti-settings settings-icon"></i>
        </div>
    </div>
    """, unsafe_allow_html=True)




# ==========================================
# MAIN AREA
# ==========================================

# Dynamic Stats Calculation
ideas_explored = sum(1 for msg in chat_history if msg["role"] == "user")
competitors_count = len(competitors)
raw_budget = startup_profile.get("estimated_budget", "Pending")
currency_code = startup_profile.get("currency", "INR")
if raw_budget in ["$0", "₹0", "0", "", None, "Pending"]:
    mvp_estimate_display = "Pending"
    mvp_delta_msg = "Waiting for input"
    mvp_delta_class = "stat-delta"
    mvp_delta_icon = "ti-clock"
else:
    mvp_estimate_display = format_currency(raw_budget, currency_code)
    mvp_delta_msg = "Optimized build"
    mvp_delta_class = "stat-delta-down"
    mvp_delta_icon = "ti-arrow-down-right"

time_to_launch_display = startup_profile.get("time_to_launch", "9 wks")
if not time_to_launch_display or time_to_launch_display == "Pending" or time_to_launch_display == "9 wks":
    if roadmap:
        time_to_launch_display = f"{len(roadmap) * 2} wks"
    else:
        time_to_launch_display = "9 wks"

if time_to_launch_display == "Pending":
    time_to_launch_status = "Needs roadmap"
    time_to_launch_color = "#f59e0b"
    time_to_launch_icon = "ti-alert-triangle"
elif len(roadmap) > 4 or time_to_launch_display == "9 wks":
    time_to_launch_status = "Needs refinement"
    time_to_launch_color = "#f59e0b"
    time_to_launch_icon = "ti-alert-triangle"
else:
    time_to_launch_status = "Optimized timeline"
    time_to_launch_color = "#10b981"
    time_to_launch_icon = "ti-circle-check"

# Prepare variables for JS Export
profile_name_encoded = urllib.parse.quote(startup_profile.get("name", "Untitled Startup"))
profile_idea_encoded = urllib.parse.quote(startup_profile.get("idea", ""))
profile_stage_encoded = urllib.parse.quote(startup_profile.get("current_stage", "Ideation"))
profile_budget_encoded = urllib.parse.quote(format_currency(startup_profile.get("estimated_budget", "Pending"), startup_profile.get("currency", "INR")))
profile_tech_encoded = urllib.parse.quote(startup_profile.get("tech_stack", ""))
profile_audience_encoded = urllib.parse.quote(startup_profile.get("target_audience", ""))
competitors_json = json.dumps(competitors)
roadmap_json = json.dumps(roadmap)

# Premium Header Banner with Stats Strip, Radial Glow Orbs, and New Session Button
active_tab = st.session_state.active_tab
st.markdown(f"""
<!-- Global Background Glow Orbs -->
<div class="global-glow glow-tr"></div>
<div class="global-glow glow-bl"></div>

<div class="header-container">
<!-- Radial Glow Orbs inside header -->
<div class="glow-orb glow-cyan"></div>
<div class="glow-orb glow-blue"></div>
<div class="header-content">
<div class="header-flex">
<div>
<div class="header-title" style="display: flex; align-items: center; gap: 10px;">
    <div style="width: 32px; height: 32px; background: linear-gradient(135deg, rgba(6,182,212,0.2), rgba(59,130,246,0.15)); border: 1px solid rgba(6,182,212,0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 2px;">{logo_html}</div>
    BuildMate AI
</div>
<div class="header-subtitle">Your Autonomous AI Startup Co-Founder & Strategy Dashboard</div>
</div>
<div class="header-actions">
<a href="/?action=new_session" target="_self" class="btn-new-session">
<i class="ti ti-refresh"></i> New session
</a>
<div class="status-badge">
<div class="status-dot"></div>
CO-FOUNDER ONLINE
</div>
</div>
</div>

<!-- 1px Gradient Divider under title row -->
<div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(6,182,212,0.15), rgba(6,182,212,0.15), transparent); margin: 1.5rem 0 1.2rem 0;"></div>

<!-- 4-Column Stats Strip inside the header card -->
<div class="stats-strip">
<div class="stat-card">
<div class="stat-label"><i class="ti ti-bulb"></i> Ideas explored</div>
<div class="stat-value">{ideas_explored}</div>
<div class="stat-delta"><i class="ti ti-arrow-up-right"></i> Active discussion</div>
</div>
<div class="stat-card">
<div class="stat-label"><i class="ti ti-search"></i> Competitors mapped</div>
<div class="stat-value">{competitors_count}</div>
<div class="stat-delta"><i class="ti ti-circle-check"></i> {competitors_count} competitors</div>
</div>
<div class="stat-card">
<div class="stat-label"><i class="ti ti-coin"></i> MVP estimate</div>
<div class="stat-value">{mvp_estimate_display}</div>
<div class="stat-delta-down"><i class="ti {mvp_delta_icon}"></i> {mvp_delta_msg}</div>
</div>
<div class="stat-card">
<div class="stat-label"><i class="ti ti-calendar"></i> Time to launch</div>
<div class="stat-value">{time_to_launch_display}</div>
<div class="stat-delta" style="color: {time_to_launch_color}; font-weight: 500;"><i class="ti {time_to_launch_icon}"></i> {time_to_launch_status}</div>
</div>
</div>

<!-- Horizontal Tabs directly under the stats strip -->
<div class="tabs-container">
<a href="/?tab=chat" target="_self" class="tab-item {"active" if active_tab == "chat" else ""}">
<i class="ti ti-message-2"></i> Co-Founder Chat
</a>
<a href="/?tab=profile" target="_self" class="tab-item {"active" if active_tab == "profile" else ""}">
<i class="ti ti-layout-grid"></i> Startup Profile
</a>
<a href="/?tab=competitors" target="_self" class="tab-item {"active" if active_tab == "competitors" else ""}">
<i class="ti ti-search"></i> Competitor Research
</a>
<a href="/?tab=budget" target="_self" class="tab-item {"active" if active_tab == "budget" else ""}">
<i class="ti ti-chart-bar"></i> MVP Budget Estimator
</a>
<a href="/?tab=roadmap" target="_self" class="tab-item {"active" if active_tab == "roadmap" else ""}">
<i class="ti ti-map-2"></i> Roadmap & Strategy
</a>
</div>

</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TAB 1: Chat Interface
# ==========================================
if st.session_state.active_tab == "chat":
    st.markdown('<div class="section-heading">💬 Co-Founder Discussion Board</div>', unsafe_allow_html=True)
    
    # Render Chat Messages using custom HTML bubbles
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg['content'])
        else:
            content = msg["content"]
            decision_log = None
            try:
                # If the message content is a JSON string, parse and extract the response text
                data = json.loads(content)
                if isinstance(data, dict):
                    content = data.get("response_text", content)
                    decision_log = data.get("decision_log")
            except Exception:
                pass
            with st.chat_message("assistant"):
                st.markdown(content)
                if decision_log:
                    st.markdown(f"""
                    <div style="margin-top: 12px; padding: 10px 14px; background: rgba(6, 182, 212, 0.04); border: 1px solid rgba(6, 182, 212, 0.12); border-radius: 8px; font-size: 0.82rem; color: #8fa0b5; animation: fadeIn 0.4s ease-out;">
                        <div style="font-weight: 700; color: #22d3ee; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                            <i class="ti ti-terminal-2"></i> Agent Decision Log
                        </div>
                        <div style="margin-bottom: 4px; display: flex; gap: 4px; align-items: center;">
                            <span style="color: #4b6a7a; font-weight: 600;">🔧 Tools Used:</span>
                            <span style="color: #bfdbfe;">{', '.join(decision_log.get('tools_used', [])) or 'None'}</span>
                        </div>
                        <div style="margin-bottom: 4px; display: flex; gap: 4px; align-items: flex-start;">
                            <span style="color: #4b6a7a; font-weight: 600; min-width: 50px;">❓ Why:</span>
                            <span style="color: #bfdbfe;">{'; '.join(decision_log.get('reasons', [])) or 'No tools required for this response.'}</span>
                        </div>
                        <div style="margin-bottom: 4px; display: flex; gap: 4px; align-items: center;">
                            <span style="color: #4b6a7a; font-weight: 600;">💾 Memory Updated:</span>
                            <span style="color: #bfdbfe;">{decision_log.get('memory_updated', 'No')}</span>
                        </div>
                        <div style="display: flex; gap: 4px; align-items: center;">
                            <span style="color: #4b6a7a; font-weight: 600;">🎯 Next Recommended Action:</span>
                            <span style="color: #67e8f9; font-weight: 600;">{decision_log.get('next_action', 'N/A')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
    # Chat Input
    if user_prompt := st.chat_input("Brainstorm with your co-founder... (e.g., 'Search for competitors' or 'Calculate my MVP cost')"):
        # Save and display user message immediately
        db.save_chat_message("user", user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        from datetime import datetime
        st.session_state.last_interaction_time = datetime.now().strftime("%I:%M %p")
        st.rerun()

    # If the last message is from user, generate assistant response
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_prompt = st.session_state.messages[-1]["content"]
        
        # Co-Founder Thinking and Response
        with st.chat_message("assistant"):
            # Show pulsing typing indicator
            typing_placeholder = st.empty()
            typing_placeholder.markdown("""
            <div class="typing-indicator" style="margin-bottom: 1rem;">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
            """, unsafe_allow_html=True)
            
            # Run the multi-step planning agent with a loading status container
            with st.status("🧠 Co-Founder is formulating strategy...", expanded=True) as status:
                reply, planning_steps = generate_co_founder_response(user_prompt, status_container=status)
                status.update(label="✅ Strategy formulated!", state="complete", expanded=False)
            
            # Remove typing indicator
            typing_placeholder.empty()
            
            # Since reply might be a JSON string, extract response_text for immediate display
            display_reply = reply
            try:
                data = json.loads(reply)
                display_reply = data.get("response_text", reply)
            except Exception:
                pass
                
            st.write(display_reply)
            db.save_chat_message("assistant", reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.toast("🧠 Startup memory updated!", icon="💾")
            st.rerun()

# ==========================================
# TAB 2: Startup Profile
# ==========================================
elif st.session_state.active_tab == "profile":
    st.markdown('<div class="section-heading">📊 Startup Performance Dashboard</div>', unsafe_allow_html=True)
    
    # 1. Overall Startup Progress Bar
    progress_pct = startup_profile.get("progress_pct", 10)
    st.markdown(f"**Overall Startup Progress: {progress_pct}%**")
    st.progress(progress_pct / 100.0)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Row of 4 Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">🚀 Current Stage</div>
            <div class="card-value" style="font-size: 1.35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {startup_profile.get('current_stage', 'Ideation')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">🔍 Competitors</div>
            <div class="card-value" style="font-size: 1.35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {len(competitors)} mapped
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        formatted_profile_budget = format_currency(startup_profile.get('estimated_budget', 'Pending'), startup_profile.get('currency', 'INR'))
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">💰 Budget Status</div>
            <div class="card-value" style="font-size: 1.35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {formatted_profile_budget}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">🗺️ Roadmap Status</div>
            <div class="card-value" style="font-size: 1.35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {startup_profile.get('roadmap_status', 'Pending')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Personalized Action Plan
    high_tasks, med_tasks, low_tasks = generate_personalized_recommendations(startup_profile, competitors, roadmap)
    
    high_tasks_html = "".join(f'<div style="font-size: 0.85rem; margin-left: 1rem; margin-bottom: 0.25rem; color: #bfdbfe;">• {task}</div>' for task in high_tasks)
    med_tasks_html = "".join(f'<div style="font-size: 0.85rem; margin-left: 1rem; margin-bottom: 0.25rem; color: #bfdbfe;">• {task}</div>' for task in med_tasks)
    low_tasks_html = "".join(f'<div style="font-size: 0.85rem; margin-left: 1rem; margin-bottom: 0.25rem; color: #bfdbfe;">• {task}</div>' for task in low_tasks)
    
    st.markdown(f"""
    <div style="background: rgba(6, 182, 212, 0.03); border: 1px solid rgba(6, 182, 212, 0.08); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; animation: fadeIn 0.4s ease-out;">
        <div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            <i class="ti ti-list-check" style="color: #22d3ee;"></i> Personalized Action Plan
        </div>
        <div style="margin-bottom: 1rem;">
            <div style="font-weight: 600; color: #f87171; font-size: 0.9rem; margin-bottom: 0.5rem;">🔴 High Priority</div>
            {high_tasks_html}
        </div>
        <div style="margin-bottom: 1rem;">
            <div style="font-weight: 600; color: #fbbf24; font-size: 0.9rem; margin-bottom: 0.5rem;">🟡 Medium Priority</div>
            {med_tasks_html}
        </div>
        <div>
            <div style="font-weight: 600; color: #34d399; font-size: 0.9rem; margin-bottom: 0.5rem;">🟢 Low Priority</div>
            {low_tasks_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 4. Core Profile Details
    st.markdown('<div class="section-heading">📋 Startup Core Profile</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">💡 Startup Name & Vision</div>
            <h3 style="color: #fff; margin-top:0.5rem; margin-bottom:0.75rem;">{startup_profile.get('name', 'Untitled Startup')}</h3>
            <p style="color: #bfdbfe; line-height: 1.6;">{startup_profile.get('idea', 'Describe your idea in the chat to populate this.')}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">🎯 Target Audience</div>
            <p style="color: #fff; font-size: 1.1rem; margin-top:0.5rem;">{startup_profile.get('target_audience', 'Not specified yet.')}</p>
        </div>
        <div class="custom-card">
            <div class="card-title">⚙️ Preferred Tech Stack</div>
            <p style="margin-top:0.5rem;"><code style="color: #22d3ee; background: rgba(6,182,212,0.1); padding: 0.25rem 0.5rem; border-radius: 4px; border: 1px solid rgba(6,182,212,0.2);">{startup_profile.get('tech_stack', 'Not specified yet.')}</code></p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 3: Competitor Research
# ==========================================
elif st.session_state.active_tab == "competitors":
    st.markdown('<div class="section-heading">🔍 Market & Competitor Landscape</div>', unsafe_allow_html=True)
    st.caption("These competitors were identified through real-time web searches.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not competitors:
        st.info("No competitor analysis available. Ask your Co-Founder in the chat to perform market research!")
    else:
        cols = st.columns(min(len(competitors), 3))
        for idx, comp in enumerate(competitors):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                st.markdown(f"""
                <div class="custom-card" style="height: 100%;">
                    <div class="card-title">🏢 Competitor</div>
                    <h3 style="color: #fff; margin-top:0.25rem; margin-bottom:0.75rem;">{comp['name']}</h3>
                    <p style="margin-bottom: 0.5rem;"><b style="color: #22d3ee;">Core Strength:</b><br>{comp['strength']}</p>
                    <p style="margin-bottom: 0;"><b style="color: #ef4444;">Weakness/Gap:</b><br>{comp['weakness']}</p>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# TAB 4: MVP Budget Estimator
# ==========================================
elif st.session_state.active_tab == "budget":
    st.markdown('<div class="section-heading">💰 MVP Budget Estimator</div>', unsafe_allow_html=True)
    st.caption("Compare development costs between India and Abroad with automatic wage adjustments and currency conversion.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_inputs, col_results = st.columns([1, 1])
    
    # Exchange Rate Constants
    EXCHANGE_RATE = 94.51
    
    with col_inputs:
        st.markdown('<div class="card-title">Cost Parameters</div>', unsafe_allow_html=True)
        
        # Region and Currency Toggles
        sel_region = st.selectbox("Development Region", ["India", "Abroad"], index=0 if startup_profile.get("currency") == "INR" or not startup_profile.get("currency") else 1)
        sel_currency = st.selectbox("Display Currency", ["INR (₹)", "USD ($)"], index=0 if startup_profile.get("currency") == "INR" or not startup_profile.get("currency") else 1)
        
        currency_code = "INR" if "INR" in sel_currency else "USD"
        symbol = "₹" if currency_code == "INR" else "$"
        
        # Calculate local wage defaults based on region and selected currency
        if sel_region == "India":
            default_dev_rate = 80000.0 if currency_code == "INR" else (80000.0 / EXCHANGE_RATE)
            default_hosting = 10000.0 if currency_code == "INR" else (10000.0 / EXCHANGE_RATE)
            default_marketing = 50000.0 if currency_code == "INR" else (50000.0 / EXCHANGE_RATE)
            default_misc = 30000.0 if currency_code == "INR" else (30000.0 / EXCHANGE_RATE)
        else:
            default_dev_rate = (5000.0 * EXCHANGE_RATE) if currency_code == "INR" else 5000.0
            default_hosting = (200.0 * EXCHANGE_RATE) if currency_code == "INR" else 200.0
            default_marketing = (2000.0 * EXCHANGE_RATE) if currency_code == "INR" else 2000.0
            default_misc = (1500.0 * EXCHANGE_RATE) if currency_code == "INR" else 1500.0
            
        # Number inputs
        dev_count = st.number_input("Number of Developers", min_value=0, max_value=20, value=2, step=1)
        months_count = st.number_input("Development Duration (Months)", min_value=1, max_value=24, value=3, step=1)
        
        dev_rate = st.number_input(f"Monthly Rate per Developer ({symbol})", min_value=0.0, value=float(default_dev_rate), step=100.0)
        hosting_cost = st.number_input(f"Monthly Hosting & Infrastructure ({symbol})", min_value=0.0, value=float(default_hosting), step=50.0)
        marketing_cost = st.number_input(f"Total Marketing & Launch Budget ({symbol})", min_value=0.0, value=float(default_marketing), step=250.0)
        misc_cost = st.number_input(f"Miscellaneous / Buffer Budget ({symbol})", min_value=0.0, value=float(default_misc), step=100.0)
        
        calculate = st.button("Calculate and Save Estimate", type="primary", use_container_width=True)

    with col_results:
        st.markdown('<div class="card-title">Cost Breakdown</div>', unsafe_allow_html=True)
        
        # Calculations
        total_dev = dev_count * months_count * dev_rate
        total_hosting = hosting_cost * months_count
        total_mvp = total_dev + total_hosting + marketing_cost + misc_cost
        
        # Converted Comparison
        alt_currency = "USD" if currency_code == "INR" else "INR"
        alt_symbol = "$" if currency_code == "INR" else "₹"
        alt_total = total_mvp / EXCHANGE_RATE if currency_code == "INR" else total_mvp * EXCHANGE_RATE
        
        if calculate:
            budget_str = f"{symbol}{total_mvp:,.2f}"
            startup_profile["estimated_budget"] = budget_str
            startup_profile["currency"] = currency_code
            from datetime import datetime
            startup_profile["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.save_startup_profile(startup_profile)
            st.balloons()
            st.toast("💰 Budget estimate saved!", icon="✅")
            st.success("Estimate saved to Startup Profile!")
            st.rerun()
            
        # Display Results
        st.metric(
            label=f"Total MVP Cost ({sel_region} / {currency_code})", 
            value=f"{symbol}{total_mvp:,.2f}",
            delta=f"Equivalent to {alt_symbol}{alt_total:,.2f} {alt_currency}"
        )
        
        st.markdown(f"""
        <div class="custom-card">
            <div class="card-title">💻 Development Payroll</div>
            <div class="card-value">{symbol}{total_dev:,.2f}</div>
            <small class="muted-text">{dev_count} Dev(s) over {months_count} month(s) @ {symbol}{dev_rate:,.2f}/mo</small>
        </div>
        <div class="custom-card">
            <div class="card-title">🌐 Infrastructure & Hosting</div>
            <div class="card-value">{symbol}{total_hosting:,.2f}</div>
            <small class="muted-text">{symbol}{hosting_cost:,.2f}/mo over {months_count} month(s)</small>
        </div>
        <div class="custom-card">
            <div class="card-title">📢 Marketing & Launch</div>
            <div class="card-value">{symbol}{marketing_cost:,.2f}</div>
        </div>
        <div class="custom-card">
            <div class="card-title">🛡️ Buffer / Misc</div>
            <div class="card-value">{symbol}{misc_cost:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# TAB 5: Roadmap
# ==========================================
elif st.session_state.active_tab == "roadmap":
    st.markdown('<div class="section-heading">🗺️ Startup Roadmap & Milestones</div>', unsafe_allow_html=True)
    st.caption("A structured strategic timeline generated by your co-founder.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not roadmap:
        st.info("No roadmap available yet. Talk to your Co-Founder in the chat to generate a roadmap!")
    else:
        for idx, milestone in enumerate(roadmap):
            status = milestone.get("status", "Pending")
            status_color = "#06b6d4" if status == "Completed" else ("#0284c7" if status == "In Progress" else "#4b6a7a")
            
            st.markdown(f"""
            <div class="custom-card" style="border-left: 4px solid {status_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #fff; font-size:1.15rem;">{milestone['title']}</h4>
                    <span class="status-pill" style="background-color: {status_color}22; color: {status_color}; border-color: {status_color}55;">
                        {status}
                    </span>
                </div>
                <p style="margin-top: 0.75rem; margin-bottom: 0; color: #bfdbfe; line-height: 1.5;">{milestone.get('desc', '')}</p>
            </div>
            """, unsafe_allow_html=True)
