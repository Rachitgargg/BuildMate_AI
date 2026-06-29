from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

@tool
def market_research_search(query: str) -> str:
    """
    Searches the web for competitors, pricing, market trends, and business insights.
    
    Why this is needed:
    LLMs have a knowledge cutoff and do not know about real-time market conditions.
    Use this tool only when the user asks for real-time market data, competitor analysis,
    or current industry trends.
    """
    search = DuckDuckGoSearchRun()
    try:
        return search.run(query)
    except Exception as e:
        # Fallback note to guide the LLM to use its own knowledge if the search API is rate-limited
        return f"[Note: The web search API is temporarily rate-limited. Please use your internal knowledge of the market to identify 2-3 realistic competitors for '{query}' and analyze their strengths and weaknesses as you normally would.]"
