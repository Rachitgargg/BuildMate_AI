import json
import os
import re
from typing import Dict, Any, List, Tuple
from agent.agent import get_llm
from tools.web_search import market_research_search
from tools.startup_cost_calculator import calculate_mvp_cost
import memory.sqlite_memory as db
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

def extract_json(text: str) -> dict:
    """
    Extracts and parses a JSON object from text, even if it contains conversational text or markdown.
    """
    def fix_json_newlines(t: str) -> str:
        result = []
        in_string = False
        escaped = False
        for char in t:
            if char == '"' and not escaped:
                in_string = not in_string
            elif char == '\\' and not escaped:
                escaped = True
            else:
                escaped = False
                
            if char == '\n' and in_string:
                result.append('\\n')
            elif char == '\r' and in_string:
                pass
            else:
                result.append(char)
        return "".join(result)

    text_clean = text.strip()
    # Try direct parse first
    try:
        return json.loads(text_clean)
    except Exception:
        pass
        
    # Remove markdown code blocks if present
    if text_clean.startswith("```"):
        # Strip ```json or ``` at start, and ``` at end
        lines = text_clean.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text_clean = "\n".join(lines).strip()
        try:
            return json.loads(fix_json_newlines(text_clean))
        except Exception:
            pass

    # Regex search for the first '{' and last '}'
    match = re.search(r'\{.*\}', text_clean, re.DOTALL)
    if match:
        try:
            return json.loads(fix_json_newlines(match.group(0)))
        except Exception:
            pass
            
    raise ValueError("Could not extract valid JSON from the model response.")

def safe_llm_invoke(llm, messages, temperature: float = 0.2):
    """
    Invokes the LLM. If it is Gemini and fails due to quota/rate limit,
    automatically falls back to Groq if GROQ_API_KEY is available.
    """
    try:
        return llm.invoke(messages)
    except Exception as e:
        err_msg = str(e)
        is_rate_limit = "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower()
        
        # Check if the current LLM is Gemini and we have a Groq fallback key
        if type(llm).__name__ == "ChatGoogleGenerativeAI" and is_rate_limit and os.getenv("GROQ_API_KEY"):
            print("⚠️ Gemini API rate limit hit. Falling back to Groq...")
            from langchain_groq import ChatGroq
            groq_llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=temperature,
                max_retries=2
            )
            return groq_llm.invoke(messages)
        else:
            raise e

def run_planning_workflow(user_input: str, status_container=None) -> Tuple[str, List[str]]:
    """
    Executes the planner-orchestrated workflow:
    1. Analyze the user's request using a classification LLM call (no tools bound).
    2. Decide in Python which tools are required.
    3. Execute tools sequentially in Python.
    4. Collect tool outputs.
    5. Build a final enriched prompt.
    6. Send the enriched prompt to Gemini using a normal llm.invoke().
    7. Parse the JSON response and save updated memory in SQLite.
    """
    steps = []
    llm = get_llm(temperature=0.2)
    
    # Load current state from SQLite
    profile = db.get_startup_profile()
    competitors = db.get_competitors()
    roadmap = db.get_roadmap()
    chat_history = db.get_chat_history()
    
    # Format current context
    context_str = f"""
    Current Startup Name: {profile.get('name')}
    Current Startup Idea: {profile.get('idea')}
    Target Audience: {profile.get('target_audience')}
    Tech Stack: {profile.get('tech_stack')}
    Estimated Budget: {profile.get('estimated_budget')}
    Currency: {profile.get('currency', 'INR')}
    """
    
    if status_container:
        status_container.write("🧠 Analyzing user request and planning workflow...")
        
    # ==========================================
    # STEP 1: Decide in Python which tools are required (via classification call)
    # ==========================================
    decision_prompt = f"""
    You are the planning brain of an AI Startup Co-founder. Analyze the user's input and decide if we need to run any of our tools to answer them.
    
    Available Tools:
    1. `market_research_search`: Use this if the user is asking for competitors, market trends, pricing, or real-time info.
    2. `calculate_mvp_cost`: Use this if the user is asking to calculate, estimate, or update the MVP budget/costs.
    
    Startup Context:
    {context_str}
    
    User Input: "{user_input}"
    
    Respond with a JSON object containing:
    "needs_search": true or false,
    "search_query": "a clean search query if true, otherwise empty string",
    "needs_calc": true or false,
    "calc_params": {{
      "developer_count": integer (default 2),
      "duration_months": integer (default 3),
      "region": "India" or "Abroad" (default "India"),
      "currency": "USD" or "INR" (default "INR"),
      "monthly_developer_rate": float or null,
      "monthly_hosting_cost": float or null,
      "total_marketing_budget": float or null,
      "misc_buffer_budget": float or null
    }} (only fill parameters if needs_calc is true, otherwise empty dict)
    
    Do not include any other text or markdown formatting like ```json. Output raw JSON only.
    """
    
    needs_search = False
    search_query = ""
    needs_calc = False
    calc_params = {}
    
    try:
        # Run classification call (No tools bound!)
        res = safe_llm_invoke(llm, [HumanMessage(content=decision_prompt)], temperature=0.2)
        decision = extract_json(res.content)
        needs_search = decision.get("needs_search", False)
        search_query = decision.get("search_query", "")
        needs_calc = decision.get("needs_calc", False)
        calc_params = decision.get("calc_params", {})
    except Exception as e:
        steps.append(f"⚠️ Error during planning decision: {str(e)}")

    # ==========================================
    # STEP 2: Execute tools sequentially in Python and collect outputs
    # ==========================================
    search_output = ""
    calc_output = ""
    
    if needs_search and search_query:
        step_msg = f"🌐 Researching competitors on the web for: '{search_query}'..."
        steps.append(step_msg)
        if status_container:
            status_container.write(step_msg)
            
        try:
            search_output = market_research_search.invoke(search_query)
            steps.append("✅ Competitor research completed.")
            if status_container:
                status_container.write("✅ Competitor research completed.")
        except Exception:
            search_output = "I couldn't complete the competitor research right now. Please try again in a moment."
            steps.append("⚠️ Web search failed.")
            
    if needs_calc and calc_params:
        # Ensure all required parameters are present and not None
        if not isinstance(calc_params, dict):
            calc_params = {}
        if calc_params.get("developer_count") is None:
            calc_params["developer_count"] = 2
        if calc_params.get("duration_months") is None:
            calc_params["duration_months"] = 3
        if not calc_params.get("region"):
            calc_params["region"] = "India"
        if not calc_params.get("currency"):
            calc_params["currency"] = "INR"

        step_msg = "💰 Estimating MVP cost using calculator..."
        steps.append(step_msg)
        if status_container:
            status_container.write(step_msg)
            
        try:
            calc_output = calculate_mvp_cost.invoke(calc_params)
            steps.append("✅ Cost estimation completed.")
            if status_container:
                status_container.write("✅ Cost estimation completed.")
        except Exception:
            calc_output = "I couldn't calculate the MVP budget estimate right now. Please try again in a moment."
            steps.append("⚠️ Cost calculation failed.")

    # ==========================================
    # STEP 3: Build final enriched prompt and invoke Gemini
    # ==========================================
    if status_container:
        status_container.write("📅 Creating roadmap & updating database...")
        
    from agent.prompts import COFOUNDER_SYSTEM_PROMPT
    formatted_system_prompt = COFOUNDER_SYSTEM_PROMPT.format(
        startup_name=profile.get("name", "Untitled Startup"),
        startup_idea=profile.get("idea", ""),
        target_audience=profile.get("target_audience", ""),
        tech_stack=profile.get("tech_stack", ""),
        estimated_budget=profile.get("estimated_budget", "₹0"),
        currency=profile.get("currency", "INR")
    )
    
    # Construct message list for final synthesis
    messages: List[BaseMessage] = [
        SystemMessage(content=formatted_system_prompt)
    ]
    
    # Add chat history (clean text)
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            content = msg["content"]
            try:
                data = json.loads(content)
                content = data.get("response_text", content)
            except Exception:
                pass
            messages.append(AIMessage(content=content))
            
    # Add the current user prompt + any tool outputs collected
    user_message_content = f"""User Request: "{user_input}"\n\n"""
    
    if search_output:
        user_message_content += f"""[Planner Note: The Web Search Tool was executed. Here are the search results:]{search_output}\n\n"""
        
    if calc_output:
        user_message_content += f"""[Planner Note: The Cost Calculator Tool was executed. Here are the calculation results:]{calc_output}\n\n"""
        
    messages.append(HumanMessage(content=user_message_content))
    
    # Invoke LLM for final response (No tools bound!)
    try:
        final_response_msg = safe_llm_invoke(llm, messages, temperature=0.7)
        output_text = final_response_msg.content
    except Exception as e:
        err_msg = str(e)
        provider = "Groq" if os.getenv("GROQ_API_KEY") else "Gemini"
        if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower():
            output_text = f"⚠️ **{provider} API Quota Exceeded**: It looks like we have hit the rate limit for the {provider} API. Please wait a minute before trying again."
        else:
            output_text = f"⚠️ **Service Error**: I encountered an issue while generating a response. Details: {err_msg}"

    # ==========================================
    # STEP 4: Parse final response and save to SQLite
    # ==========================================
    try:
        data = extract_json(output_text)
        
        # Construct decision log
        decision_log = {
            "tools_used": [],
            "reasons": [],
            "memory_updated": "No",
            "next_action": "Continue discussing and refining the startup details."
        }
        if needs_search:
            decision_log["tools_used"].append("market_research_search")
            decision_log["reasons"].append("To identify and analyze key competitors in the market based on the user's startup idea.")
        if needs_calc:
            decision_log["tools_used"].append("calculate_mvp_cost")
            decision_log["reasons"].append("To calculate a detailed, localized cost estimation for the startup's MVP.")
            
        updated_fields = []
        updated_profile = data.get("updated_profile", {})
        updated_competitors = data.get("updated_competitors", [])
        updated_roadmap = data.get("updated_roadmap", [])
        
        if updated_profile:
            updated_fields.append("Startup Profile")
        if updated_competitors:
            updated_fields.append("Competitors List")
        if updated_roadmap:
            updated_fields.append("Roadmap Milestones")
        if updated_fields:
            decision_log["memory_updated"] = f"Yes ({', '.join(updated_fields)})"
            
        # Determine next recommended action based on current state
        if not profile.get("idea") and not (updated_profile and updated_profile.get("idea")):
            decision_log["next_action"] = "Define the core startup idea and target audience."
        elif not competitors and not updated_competitors:
            decision_log["next_action"] = "Run a competitor research search to map the competitive landscape."
        elif (profile.get("estimated_budget") in ["$0", "₹0", "0", "", None, "Pending"]) and not (updated_profile and updated_profile.get("estimated_budget")):
            decision_log["next_action"] = "Calculate the MVP budget estimate using the cost calculator."
        elif not roadmap and not updated_roadmap:
            decision_log["next_action"] = "Generate a structured startup roadmap and milestone timeline."
        else:
            decision_log["next_action"] = "Refine the MVP tech stack or proceed to the launch preparation phase."

        data["decision_log"] = decision_log
        clean_output = json.dumps(data)
        
        # Save updated profile
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # We always update the profile to record the last_updated timestamp on every interaction
        merged_profile = {**profile, **updated_profile}
        merged_profile["last_updated"] = timestamp
        
        db.save_startup_profile(merged_profile)
            
        # Save competitors
        if updated_competitors:
            db.save_competitors(updated_competitors)
            
        # Save roadmap
        if updated_roadmap:
            db.save_roadmap(updated_roadmap)
            
        if status_container:
            status_container.write("🧠 Saving startup memory...")
            status_container.write("✅ Analysis complete.")
            
        return clean_output, steps
        
    except Exception as e:
        if status_container:
            status_container.write(f"⚠️ Output was not in JSON format. Saving raw response. Error: {str(e)}")
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save timestamp even on fallback
        profile["last_updated"] = timestamp
        db.save_startup_profile(profile)
        
        fallback_json = json.dumps({
            "response_text": output_text,
            "updated_profile": {},
            "updated_competitors": [],
            "updated_roadmap": [],
            "decision_log": {
                "tools_used": [],
                "reasons": [],
                "memory_updated": "No",
                "next_action": "Introduce your startup idea to the co-founder."
            }
        })
        return fallback_json, steps
