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
        return f"Error performing web search: {str(e)}"
