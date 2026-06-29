from langchain_core.tools import tool

EXCHANGE_RATE = 94.51  # 1 USD = 94.51 INR

# Typical wage/cost defaults
DEFAULTS = {
    "India": {
        "dev_rate_inr": 80000.0,       # ₹80,000/month
        "hosting_inr": 10000.0,        # ₹10,000/month
        "marketing_inr": 50000.0,      # ₹50,000
        "buffer_inr": 30000.0          # ₹30,000
    },
    "Abroad": {
        "dev_rate_usd": 5000.0,        # $5,000/month
        "hosting_usd": 200.0,          # $200/month
        "marketing_usd": 2000.0,       # $2,000
        "buffer_usd": 1500.0           # $1,500
    }
}

@tool
def calculate_mvp_cost(
    developer_count: int,
    duration_months: int,
    region: str,  # 'India' or 'Abroad'
    currency: str,  # 'USD' or 'INR'
    monthly_developer_rate: float = None,
    monthly_hosting_cost: float = None,
    total_marketing_budget: float = None,
    misc_buffer_budget: float = None
) -> str:
    """
    Calculates the estimated total MVP development cost based on staffing, infrastructure, and marketing.
    Supports currency conversion (USD/INR) and accounts for wage differences between India and Abroad.
    
    Why this is needed:
    Wages in India are typically 4-5x lower than Abroad. This tool dynamically adjusts default rates
    based on the selected region and handles currency conversions accurately.
    
    Parameters:
    - developer_count: Number of developers needed.
    - duration_months: Estimated development duration in months.
    - region: The development region ('India' or 'Abroad').
    - currency: The output currency ('USD' or 'INR').
    - monthly_developer_rate: Custom monthly rate per developer (optional).
    - monthly_hosting_cost: Custom monthly hosting cost (optional).
    - total_marketing_budget: Custom total marketing budget (optional).
    - misc_buffer_budget: Custom miscellaneous buffer budget (optional).
    """
    # Normalize inputs
    region = "India" if "india" in region.lower() else "Abroad"
    currency = "INR" if "inr" in currency.upper() else "USD"
    
    # Get defaults based on region
    if region == "India":
        # Defaults are in INR
        d_rate = monthly_developer_rate if monthly_developer_rate is not None else DEFAULTS["India"]["dev_rate_inr"]
        d_host = monthly_hosting_cost if monthly_hosting_cost is not None else DEFAULTS["India"]["hosting_inr"]
        d_market = total_marketing_budget if total_marketing_budget is not None else DEFAULTS["India"]["marketing_inr"]
        d_buffer = misc_buffer_budget if misc_buffer_budget is not None else DEFAULTS["India"]["buffer_inr"]
        
        # If currency is USD, convert India INR defaults to USD
        if currency == "USD":
            d_rate = d_rate / EXCHANGE_RATE
            d_host = d_host / EXCHANGE_RATE
            d_market = d_market / EXCHANGE_RATE
            d_buffer = d_buffer / EXCHANGE_RATE
    else:
        # Defaults are in USD
        d_rate = monthly_developer_rate if monthly_developer_rate is not None else DEFAULTS["Abroad"]["dev_rate_usd"]
        d_host = monthly_hosting_cost if monthly_hosting_cost is not None else DEFAULTS["Abroad"]["hosting_usd"]
        d_market = total_marketing_budget if total_marketing_budget is not None else DEFAULTS["Abroad"]["marketing_usd"]
        d_buffer = misc_buffer_budget if misc_buffer_budget is not None else DEFAULTS["Abroad"]["buffer_usd"]
        
        # If currency is INR, convert Abroad USD defaults to INR
        if currency == "INR":
            d_rate = d_rate * EXCHANGE_RATE
            d_host = d_host * EXCHANGE_RATE
            d_market = d_market * EXCHANGE_RATE
            d_buffer = d_buffer * EXCHANGE_RATE

    # Perform calculations
    total_dev = developer_count * duration_months * d_rate
    total_hosting = d_host * duration_months
    total_cost = total_dev + total_hosting + d_market + d_buffer
    
    # Calculate converted values for comparison
    sym = "₹" if currency == "INR" else "$"
    alt_sym = "$" if currency == "INR" else "₹"
    alt_total = total_cost / EXCHANGE_RATE if currency == "INR" else total_cost * EXCHANGE_RATE
    
    return f"""
=== MVP Cost Estimate Breakdown ({region} / {currency}) ===
- Region: {region} (Wages adjusted for local rates)
- Development Payroll: {sym}{total_dev:,.2f} ({developer_count} dev(s) for {duration_months} month(s) @ {sym}{d_rate:,.2f}/mo)
- Infrastructure & Hosting: {sym}{total_hosting:,.2f} ({sym}{d_host:,.2f}/mo for {duration_months} month(s))
- Marketing & Launch: {sym}{d_market:,.2f}
- Miscellaneous Buffer: {sym}{d_buffer:,.2f}
----------------------------------
TOTAL ESTIMATED MVP COST: {sym}{total_cost:,.2f}
(Equivalent to approx: {alt_sym}{alt_total:,.2f})
==================================
"""
