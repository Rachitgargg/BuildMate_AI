import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from agent.prompts import COFOUNDER_SYSTEM_PROMPT
from tools.web_search import market_research_search
from tools.startup_cost_calculator import calculate_mvp_cost

# Load environment variables from .env
load_dotenv()

def get_llm(temperature: float = 0.7):
    """
    Initializes and returns the LLM instance.
    Prefers Gemini if GEMINI_API_KEY is set, otherwise falls back to Groq.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=temperature,
            max_retries=3,
        )
        
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key,
            temperature=temperature,
            max_retries=2
        )
        
    raise ValueError(
        "Neither GEMINI_API_KEY nor GROQ_API_KEY found. Please set one in your .env file."
    )

def get_agent_executor(tools: List[Any] = None) -> AgentExecutor:
    """
    Creates and returns a LangChain AgentExecutor.
    
    Why this is used:
    An AgentExecutor is the runtime for an agent. It takes the agent design,
    the list of tools, and handles the loop of:
    1. Running the agent to get a decision (text response or tool call).
    2. Executing the tool if requested.
    3. Passing the tool output back to the agent.
    4. Repeating until the agent decides to give a final text answer.
    """
    if tools is None:
        tools = []
        
    llm = get_llm()
    
    # Define the prompt structure
    # We use MessagesPlaceholder for 'chat_history' to pass the conversation history.
    # We use MessagesPlaceholder for 'agent_scratchpad' which is where LangChain
    # stores the intermediate tool calls and their results so the LLM knows what it did.
    import memory.sqlite_memory as db
    profile = db.get_startup_profile() or {}
    
    formatted_system_prompt = COFOUNDER_SYSTEM_PROMPT.format(
        startup_name=profile.get("name", "Untitled Startup"),
        startup_idea=profile.get("idea", ""),
        target_audience=profile.get("target_audience", ""),
        tech_stack=profile.get("tech_stack", ""),
        estimated_budget=profile.get("estimated_budget", "₹0"),
        currency=profile.get("currency", "INR")
    )
    
    from langchain_core.messages import SystemMessage
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=formatted_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create the agent using Gemini's native tool-calling capabilities
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create and return the executor
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # Prints the agent's reasoning process in the terminal
        handle_parsing_errors=True # Gracefully handle any formatting issues
    )

def generate_co_founder_response(user_input: str, status_container=None) -> tuple[str, list[str]]:
    """
    Generates a response using the multi-step planning workflow.
    Returns a tuple of (response_text, list_of_planning_steps).
    """
    from agent.planner import run_planning_workflow
    return run_planning_workflow(user_input, status_container)
