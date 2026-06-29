# ⚡ BuildMate AI - Autonomous Startup Co-Founder & Strategy Dashboard

**BuildMate AI** is an autonomous AI-powered startup co-founder and strategy console designed to help founders brainstorm ideas, map out competitors, calculate MVP budgets, and generate structured roadmarks.

---

## 🚀 Key Features

* **AI Co-Founder Chat**: Brainstorm your startup concept, target audience, and tech stack in real-time with an intelligent, agentic co-founder powered by Gemini/Groq.
* **Agent Decision Log**: Transparently view which tools the AI used (e.g., Cost Calculator or Web Search), why they were used, and the next recommended actions.
* **Personalized Action Plan**: Dynamically generates prioritized tasks (🔴 High, 🟡 Medium, 🟢 Low Priority) based on your startup idea, current stage, budget, and competitor landscape.
* **Competitor Research**: Automatically searches the web to map out key competitors, highlighting their core strengths and weaknesses.
* **MVP Budget Estimator**: Calculates localized MVP development costs across different regions (e.g., India, US, Europe) with proper currency formatting.
* **Roadmap & Strategy**: Generates a structured 30-day timeline with milestones to guide your project from ideation to launch.
* **Persistent Memory State**: Displays your startup profile, stage, budget, and last updated timestamp in a persistent sidebar panel powered by a local SQLite database.

---

## 🛠️ Local Installation & Hosting

Follow these steps to set up and run BuildMate AI locally on your system:

### 1. Clone the Repository
```bash
git clone https://github.com/Rachitgargg/BuildMate_AI.git
cd BuildMate_AI
```

### 2. Create and Activate a Virtual Environment
```bash
# Create a virtual environment
python3 -m venv venv

# Activate on macOS/Linux:
source venv/bin/activate

# Activate on Windows (Command Prompt):
# venv\Scripts\activate.bat

# Activate on Windows (PowerShell):
# .\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory of the project and add your API keys:
```env
# Add either Gemini (Recommended) or Groq API Key
GEMINI_API_KEY="your_gemini_api_key_here"

# Optional: if you prefer to use Groq
# GROQ_API_KEY="your_groq_api_key_here"
```

### 5. Run the Application
Start the Streamlit console:
```bash
streamlit run app.py
```

The application will automatically open in your default browser at `http://localhost:8501`.

---

## 📂 Project Structure

```text
├── app.py                     # Main Streamlit Dashboard & UI
├── requirements.txt           # Python Dependencies
├── .env.example               # Template for environment variables
├── .gitignore                 # Git ignore rules (excludes private keys & databases)
├── assets/
│   └── logo.png               # Custom Brand Logo
├── agent/
│   ├── agent.py               # LLM initialization and executor setup
│   ├── planner.py             # Multi-step planning workflow and tool execution
│   └── prompts.py             # System prompts and instructions
├── memory/
│   └── sqlite_memory.py       # SQLite database helper for persistent state
├── tools/
│   ├── startup_cost_calculator.py  # Localized MVP cost calculator tool
│   └── web_search.py          # Market research Google Search tool
└── utils/
    └── __init__.py            # Utility helper files
```