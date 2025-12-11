"""
UAE Mortgage Assistant Agent - Built with Google ADK + LiteLLM (Groq).

This agent acts as a "Smart Friend" helping expats understand UAE mortgages,
make buy vs rent decisions, and avoid common pitfalls.

The agent delegates all math to deterministic tools to avoid hallucination.
Uses LiteLLM to connect to Groq for fast inference.
"""

import os
from pathlib import Path

from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.models.lite_llm import LiteLlm

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our deterministic calculation tools
from .tools import (
    tool_calculate_mortgage,
    tool_assess_affordability,
    tool_compare_buy_vs_rent,
    tool_check_eligibility,
    tool_get_uae_mortgage_rules,
)


def load_system_prompt() -> str:
    """Load the system prompt from file."""
    prompt_path = Path(__file__).parent / "prompts" / "system.txt"
    if prompt_path.exists():
        return prompt_path.read_text()
    # Fallback prompt if file not found
    return """You are Ramy, a friendly UAE mortgage advisor. 
    Help users understand mortgages, calculate EMI, and make buy vs rent decisions.
    ALWAYS use the provided tools for calculations - never estimate numbers yourself."""


# Define the tools for the ADK agent
mortgage_calculator = FunctionTool(func=tool_calculate_mortgage)
affordability_checker = FunctionTool(func=tool_assess_affordability)
buy_vs_rent_analyzer = FunctionTool(func=tool_compare_buy_vs_rent)
eligibility_checker = FunctionTool(func=tool_check_eligibility)
rules_explainer = FunctionTool(func=tool_get_uae_mortgage_rules)


# Get model name from environment (defaults to Groq's llama)
MODEL_NAME = os.getenv("MODEL_NAME", "groq/llama-3.3-70b-versatile")

# Create LiteLLM model wrapper for Groq
# Set temperature=0 and top_p=1 for deterministic, reliable tool calling
groq_model = LiteLlm(
    model=MODEL_NAME,
    temperature=0,
    top_p=1,
)


# Create the root agent with Google ADK using LiteLLM
root_agent = Agent(
    name="mortgage_advisor",
    model=groq_model,
    description="A friendly UAE mortgage advisor that helps expats make smart buy vs rent decisions",
    instruction=load_system_prompt(),
    tools=[
        mortgage_calculator,
        affordability_checker,
        buy_vs_rent_analyzer,
        eligibility_checker,
        rules_explainer,
    ],
)


# For compatibility - expose tool metadata
MORTGAGE_TOOLS = [
    {
        "name": "tool_calculate_mortgage",
        "description": """Calculate mortgage EMI and total costs for a property. 
        Use when user mentions a property price and wants monthly payment.
        Returns: Monthly EMI, total interest, upfront costs breakdown.""",
        "function": tool_calculate_mortgage,
        "parameters": {
            "property_price": {
                "type": "number",
                "description": "Property price in AED (e.g., 2000000 for 2M)"
            },
            "down_payment_percent": {
                "type": "number", 
                "description": "Down payment %, minimum 20 for expats. Default: 20"
            },
            "interest_rate": {
                "type": "number",
                "description": "Annual interest rate %. Default: 4.5"
            },
            "tenure_years": {
                "type": "integer",
                "description": "Loan tenure in years, max 25. Default: 25"
            }
        },
        "required": ["property_price"]
    },
    {
        "name": "tool_assess_affordability",
        "description": """Assess what property price a user can afford based on income.
        Use when user mentions their income and wants to know budget.
        Returns: Maximum property price, recommended comfortable budget.""",
        "function": tool_assess_affordability,
        "parameters": {
            "monthly_income": {
                "type": "number",
                "description": "User's gross monthly income in AED"
            },
            "existing_monthly_debts": {
                "type": "number",
                "description": "Other monthly debts (car loan, etc). Default: 0"
            },
            "desired_property_price": {
                "type": "number",
                "description": "Optional: specific property to check affordability"
            }
        },
        "required": ["monthly_income"]
    },
    {
        "name": "tool_compare_buy_vs_rent",
        "description": """Compare buying vs renting with detailed analysis.
        Use when user wants to decide between buying and renting.
        Returns: Clear recommendation (BUY/RENT/BORDERLINE) with reasoning.""",
        "function": tool_compare_buy_vs_rent,
        "parameters": {
            "property_price": {
                "type": "number",
                "description": "Price of property they're considering in AED"
            },
            "monthly_rent": {
                "type": "number",
                "description": "Current/comparable monthly rent in AED"
            },
            "years_staying": {
                "type": "integer",
                "description": "How many years they plan to stay in UAE"
            },
            "down_payment_percent": {
                "type": "number",
                "description": "Down payment %, minimum 20. Default: 20"
            }
        },
        "required": ["property_price", "monthly_rent", "years_staying"]
    },
    {
        "name": "tool_check_eligibility",
        "description": """Check if user is eligible for UAE mortgage.
        Use to validate basic eligibility requirements.
        Returns: Eligibility status with issues and required documents.""",
        "function": tool_check_eligibility,
        "parameters": {
            "is_expat": {
                "type": "boolean",
                "description": "True if not UAE national. Default: True"
            },
            "monthly_income": {
                "type": "number",
                "description": "Gross monthly income in AED"
            },
            "is_self_employed": {
                "type": "boolean",
                "description": "True if self-employed or business owner"
            },
            "years_in_uae": {
                "type": "number",
                "description": "Years of UAE residency"
            }
        },
        "required": []
    },
    {
        "name": "tool_get_uae_mortgage_rules",
        "description": """Get key UAE mortgage rules and constraints.
        Use when asked about regulations, LTV limits, fees, or requirements.
        Returns: Summary of all important UAE mortgage rules.""",
        "function": tool_get_uae_mortgage_rules,
        "parameters": {},
        "required": []
    }
]


# Expose tools for direct access
__all__ = [
    "root_agent",
    "MORTGAGE_TOOLS",
    "load_system_prompt",
    "tool_calculate_mortgage",
    "tool_assess_affordability", 
    "tool_compare_buy_vs_rent",
    "tool_check_eligibility",
    "tool_get_uae_mortgage_rules",
]
