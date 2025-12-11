"""
Deterministic Mortgage Calculation Tools.

These tools handle all mathematical calculations to prevent LLM hallucination.
The LLM should ALWAYS delegate math to these functions.
"""

from typing import Optional
from dataclasses import dataclass
import math


# ============================================================================
# UAE MORTGAGE CONSTANTS (Hard Rules - Never Let LLM Guess These)
# ============================================================================

MAX_LTV_EXPAT = 0.80  # 80% maximum loan for expats
MAX_LTV_UAE_NATIONAL = 0.85  # 85% for UAE nationals
TRANSFER_FEE_PERCENT = 4.0  # Dubai Land Department fee
AGENCY_FEE_PERCENT = 2.0  # Real estate agent commission
MISC_FEES_PERCENT = 1.0  # Valuation, mortgage registration, etc.
TOTAL_UPFRONT_COSTS_PERCENT = 7.0  # Total hidden costs
DEFAULT_INTEREST_RATE = 4.5  # Standard market rate
MAX_TENURE_YEARS = 25
MAINTENANCE_FEE_PERCENT = 1.5  # Annual maintenance as % of property value


@dataclass
class EMIResult:
    """Result of EMI calculation."""
    monthly_emi: float
    total_payment: float
    total_interest: float
    loan_amount: float
    tenure_months: int
    interest_rate: float


@dataclass
class AffordabilityResult:
    """Result of affordability assessment."""
    max_property_price: float
    max_loan_amount: float
    recommended_emi: float
    dti_ratio: float
    is_affordable: bool
    warning_message: Optional[str] = None


@dataclass 
class BuyVsRentResult:
    """Result of buy vs rent analysis."""
    recommendation: str  # "BUY", "RENT", or "BORDERLINE"
    monthly_buy_cost: float
    monthly_rent_cost: float
    break_even_years: float
    equity_after_period: float
    total_rent_cost: float
    total_buy_cost: float
    savings_if_buying: float
    reasoning: str


@dataclass
class UpfrontCostsResult:
    """Breakdown of upfront costs."""
    property_price: float
    down_payment: float
    transfer_fee: float
    agency_fee: float
    misc_fees: float
    total_upfront: float
    total_cash_needed: float


# ============================================================================
# CORE CALCULATION FUNCTIONS (Deterministic - No LLM Hallucination)
# ============================================================================

def calculate_emi(
    property_price: float,
    down_payment_percent: float = 20.0,
    annual_interest_rate: float = DEFAULT_INTEREST_RATE,
    tenure_years: int = 25
) -> dict:
    """
    Calculate EMI (Equated Monthly Installment) for a mortgage.
    
    This is a deterministic calculation that the LLM MUST use for all
    mortgage payment calculations. Never let the LLM guess these numbers.
    
    Args:
        property_price: Total property value in AED
        down_payment_percent: Down payment as percentage (minimum 20% for expats)
        annual_interest_rate: Annual interest rate in percent (default 4.5%)
        tenure_years: Loan tenure in years (maximum 25)
    
    Returns:
        Dictionary with EMI details including monthly payment, total interest, etc.
    """
    # Validate and enforce constraints
    down_payment_percent = max(down_payment_percent, 20.0)  # Expat minimum
    tenure_years = min(tenure_years, MAX_TENURE_YEARS)
    
    # Calculate loan amount
    down_payment = property_price * (down_payment_percent / 100)
    loan_amount = property_price - down_payment
    
    # Convert annual rate to monthly rate
    monthly_rate = (annual_interest_rate / 100) / 12
    tenure_months = tenure_years * 12
    
    # EMI Formula: EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    if monthly_rate > 0:
        emi_numerator = loan_amount * monthly_rate * math.pow(1 + monthly_rate, tenure_months)
        emi_denominator = math.pow(1 + monthly_rate, tenure_months) - 1
        monthly_emi = emi_numerator / emi_denominator
    else:
        monthly_emi = loan_amount / tenure_months
    
    total_payment = monthly_emi * tenure_months
    total_interest = total_payment - loan_amount
    
    return {
        "monthly_emi": round(monthly_emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "loan_amount": round(loan_amount, 2),
        "down_payment": round(down_payment, 2),
        "tenure_months": tenure_months,
        "tenure_years": tenure_years,
        "interest_rate": annual_interest_rate,
        "property_price": property_price
    }


def calculate_upfront_costs(property_price: float, down_payment_percent: float = 20.0) -> dict:
    """
    Calculate all upfront costs for buying a property in UAE.
    
    This is the "hidden killer" that many buyers don't account for.
    Total upfront costs are approximately 7% ON TOP of the property price.
    
    Args:
        property_price: Property value in AED
        down_payment_percent: Down payment percentage (minimum 20%)
    
    Returns:
        Breakdown of all upfront costs
    """
    down_payment_percent = max(down_payment_percent, 20.0)
    
    down_payment = property_price * (down_payment_percent / 100)
    transfer_fee = property_price * (TRANSFER_FEE_PERCENT / 100)
    agency_fee = property_price * (AGENCY_FEE_PERCENT / 100)
    misc_fees = property_price * (MISC_FEES_PERCENT / 100)
    
    total_fees = transfer_fee + agency_fee + misc_fees
    total_cash_needed = down_payment + total_fees
    
    return {
        "property_price": round(property_price, 2),
        "down_payment": round(down_payment, 2),
        "down_payment_percent": down_payment_percent,
        "transfer_fee": round(transfer_fee, 2),
        "transfer_fee_label": f"{TRANSFER_FEE_PERCENT}% (Dubai Land Dept)",
        "agency_fee": round(agency_fee, 2),
        "agency_fee_label": f"{AGENCY_FEE_PERCENT}% (Agent Commission)",
        "misc_fees": round(misc_fees, 2),
        "misc_fees_label": f"{MISC_FEES_PERCENT}% (Valuation, Registration)",
        "total_fees": round(total_fees, 2),
        "total_fees_percent": TOTAL_UPFRONT_COSTS_PERCENT,
        "total_cash_needed": round(total_cash_needed, 2),
        "warning": f"⚠️ You need {round(total_cash_needed, 0):,.0f} AED in CASH to buy (not just {round(down_payment, 0):,.0f} AED down payment!)"
    }


def calculate_affordability(
    monthly_income: float,
    monthly_expenses: float = 0,
    existing_debts: float = 0,
    max_dti_ratio: float = 50.0
) -> dict:
    """
    Calculate how much property a user can afford based on their income.
    
    Uses debt-to-income (DTI) ratio to determine maximum affordable EMI.
    
    Args:
        monthly_income: Gross monthly income in AED
        monthly_expenses: Fixed monthly expenses
        existing_debts: Existing monthly debt payments (car loans, credit cards)
        max_dti_ratio: Maximum allowed debt-to-income ratio (default 50%)
    
    Returns:
        Affordability assessment with maximum property price
    """
    # Available income for mortgage after other obligations
    available_for_debt = monthly_income * (max_dti_ratio / 100)
    max_emi = available_for_debt - existing_debts
    
    if max_emi <= 0:
        return {
            "is_affordable": False,
            "max_emi": 0,
            "max_loan_amount": 0,
            "max_property_price": 0,
            "dti_ratio": 100,
            "warning": "⚠️ Your existing debts are too high. You need to reduce debts before considering a mortgage."
        }
    
    # Reverse EMI calculation to find max loan amount
    # For 25 years at 4.5%, the EMI factor is approximately 0.00556
    tenure_years = 25
    annual_rate = DEFAULT_INTEREST_RATE
    monthly_rate = (annual_rate / 100) / 12
    tenure_months = tenure_years * 12
    
    # Loan = EMI × ((1 + r)^n - 1) / (r × (1 + r)^n)
    multiplier = (math.pow(1 + monthly_rate, tenure_months) - 1) / \
                 (monthly_rate * math.pow(1 + monthly_rate, tenure_months))
    max_loan = max_emi * multiplier
    
    # Property price = Loan / 0.8 (since expats can only borrow 80%)
    max_property_price = max_loan / MAX_LTV_EXPAT
    
    # Calculate actual DTI
    dti = ((max_emi + existing_debts) / monthly_income) * 100
    
    # Recommendations
    comfortable_emi = max_emi * 0.7  # 70% of max for comfort
    is_comfortable = monthly_expenses < (monthly_income * 0.4)
    
    return {
        "is_affordable": True,
        "max_emi": round(max_emi, 2),
        "recommended_emi": round(comfortable_emi, 2),
        "max_loan_amount": round(max_loan, 2),
        "max_property_price": round(max_property_price, 2),
        "comfortable_property_price": round(max_property_price * 0.7, 2),
        "dti_ratio": round(dti, 1),
        "monthly_income": monthly_income,
        "existing_debts": existing_debts,
        "note": "💡 Comfortable budget is 70% of maximum to leave room for emergencies."
    }


def analyze_buy_vs_rent(
    property_price: float,
    current_monthly_rent: float,
    years_planning_to_stay: int,
    down_payment_percent: float = 20.0,
    annual_interest_rate: float = DEFAULT_INTEREST_RATE,
    expected_appreciation_percent: float = 3.0,
    annual_rent_increase_percent: float = 5.0
) -> dict:
    """
    Comprehensive buy vs rent analysis based on UAE market conditions.
    
    Key Heuristics:
    - < 3 years: Almost always rent (transaction costs kill profit)
    - 3-5 years: Borderline, depends on numbers
    - > 5 years: Usually buy (equity buildup beats rent)
    
    Args:
        property_price: Property value in AED
        current_monthly_rent: Current monthly rent for similar property
        years_planning_to_stay: How long user plans to stay in UAE
        down_payment_percent: Down payment (minimum 20%)
        annual_interest_rate: Mortgage rate (default 4.5%)
        expected_appreciation_percent: Expected property value growth
        annual_rent_increase_percent: Expected annual rent increase
    
    Returns:
        Detailed buy vs rent analysis with recommendation
    """
    down_payment_percent = max(down_payment_percent, 20.0)
    months = years_planning_to_stay * 12
    
    # Calculate EMI
    emi_result = calculate_emi(
        property_price=property_price,
        down_payment_percent=down_payment_percent,
        annual_interest_rate=annual_interest_rate,
        tenure_years=min(years_planning_to_stay, 25)
    )
    monthly_emi = emi_result["monthly_emi"]
    
    # Calculate upfront costs
    upfront = calculate_upfront_costs(property_price, down_payment_percent)
    total_upfront = upfront["total_cash_needed"]
    
    # Monthly maintenance (approximately 1.5% of property value per year)
    monthly_maintenance = (property_price * MAINTENANCE_FEE_PERCENT / 100) / 12
    
    # Total monthly cost of ownership
    monthly_buy_cost = monthly_emi + monthly_maintenance
    
    # Calculate rent over time with increases
    total_rent = 0
    current_rent = current_monthly_rent
    for year in range(years_planning_to_stay):
        total_rent += current_rent * 12
        current_rent *= (1 + annual_rent_increase_percent / 100)
    
    # Average monthly rent over period
    avg_monthly_rent = total_rent / months if months > 0 else current_monthly_rent
    
    # Calculate equity buildup
    loan_amount = emi_result["loan_amount"]
    monthly_rate = (annual_interest_rate / 100) / 12
    
    # Principal paid in first 'months' of mortgage
    principal_paid = 0
    remaining_balance = loan_amount
    for _ in range(min(months, emi_result["tenure_months"])):
        interest_portion = remaining_balance * monthly_rate
        principal_portion = monthly_emi - interest_portion
        principal_paid += principal_portion
        remaining_balance -= principal_portion
    
    # Property value after appreciation
    future_value = property_price * math.pow(1 + expected_appreciation_percent / 100, years_planning_to_stay)
    appreciation_gain = future_value - property_price
    
    # Total equity = Down payment + Principal paid + Appreciation
    down_payment = upfront["down_payment"]
    equity_buildup = down_payment + principal_paid + appreciation_gain
    
    # Total cost comparison
    total_buy_cost = total_upfront + (monthly_buy_cost * months)
    total_rent_cost = total_rent
    
    # Net position (equity minus total costs vs rent)
    # If buying: you paid X but have equity worth Y
    # If renting: you paid Z and have 0 equity
    net_buy_position = equity_buildup - total_buy_cost
    net_rent_position = -total_rent_cost
    
    savings_if_buying = equity_buildup - (total_buy_cost - total_rent_cost)
    
    # Calculate break-even point
    # When does equity buildup = cumulative rent saved?
    if monthly_buy_cost > current_monthly_rent:
        # Buying costs more monthly, but builds equity
        annual_equity_gain = (principal_paid / years_planning_to_stay) + \
                            (appreciation_gain / years_planning_to_stay)
        annual_extra_cost = (monthly_buy_cost - current_monthly_rent) * 12
        if annual_equity_gain > 0:
            break_even_years = total_upfront / (annual_equity_gain - annual_extra_cost) \
                              if annual_equity_gain > annual_extra_cost else 99
        else:
            break_even_years = 99
    else:
        break_even_years = total_upfront / ((current_monthly_rent - monthly_buy_cost) * 12 + \
                          (principal_paid / years_planning_to_stay))
    
    break_even_years = max(0, min(break_even_years, 99))
    
    # Generate recommendation
    if years_planning_to_stay < 3:
        recommendation = "RENT"
        reasoning = (
            f"🏠 **Recommendation: Keep Renting**\n\n"
            f"At {years_planning_to_stay} years, the ~7% transaction fees ({round(total_upfront - down_payment):,} AED) "
            f"will eat into any potential gains. You need at least 3-4 years to recover these costs.\n\n"
            f"**Your rent over {years_planning_to_stay} years:** {round(total_rent):,} AED\n"
            f"**Buying costs (excluding equity):** {round(total_buy_cost):,} AED"
        )
    elif years_planning_to_stay <= 5:
        if savings_if_buying > 50000:
            recommendation = "BUY"
            reasoning = (
                f"🏠 **Recommendation: Consider Buying**\n\n"
                f"For {years_planning_to_stay} years, buying starts to make sense. "
                f"You'll build {round(equity_buildup):,} AED in equity while paying roughly "
                f"similar monthly costs.\n\n"
                f"**Net benefit vs renting:** ~{round(savings_if_buying):,} AED"
            )
        elif savings_if_buying < -50000:
            recommendation = "RENT"
            reasoning = (
                f"🏠 **Recommendation: Keep Renting**\n\n"
                f"The numbers don't favor buying for your {years_planning_to_stay}-year timeline. "
                f"The upfront costs and monthly difference would cost you ~{round(-savings_if_buying):,} AED "
                f"more than renting."
            )
        else:
            recommendation = "BORDERLINE"
            reasoning = (
                f"🏠 **It's a Close Call**\n\n"
                f"For {years_planning_to_stay} years, buying and renting are financially similar. "
                f"Consider your personal preferences:\n"
                f"- Want stability and to customize your home? **Buy**\n"
                f"- Want flexibility to move? **Rent**\n\n"
                f"**Difference:** Only ~{abs(round(savings_if_buying)):,} AED over {years_planning_to_stay} years"
            )
    else:
        recommendation = "BUY"
        reasoning = (
            f"🏠 **Recommendation: Buy**\n\n"
            f"At {years_planning_to_stay}+ years, buying makes strong financial sense. "
            f"You'll build significant equity while rent keeps increasing {annual_rent_increase_percent}% per year.\n\n"
            f"**Equity after {years_planning_to_stay} years:** {round(equity_buildup):,} AED\n"
            f"**If you rented instead:** {round(total_rent):,} AED gone forever\n"
            f"**Break-even point:** ~{round(break_even_years, 1)} years"
        )
    
    return {
        "recommendation": recommendation,
        "reasoning": reasoning,
        "monthly_breakdown": {
            "mortgage_emi": round(monthly_emi, 2),
            "maintenance": round(monthly_maintenance, 2),
            "total_monthly_buy_cost": round(monthly_buy_cost, 2),
            "current_monthly_rent": current_monthly_rent,
            "difference": round(monthly_buy_cost - current_monthly_rent, 2)
        },
        "cumulative_analysis": {
            "total_buy_cost": round(total_buy_cost, 2),
            "total_rent_cost": round(total_rent_cost, 2),
            "equity_buildup": round(equity_buildup, 2),
            "savings_if_buying": round(savings_if_buying, 2),
            "break_even_years": round(break_even_years, 1)
        },
        "upfront_costs": upfront,
        "assumptions": {
            "interest_rate": f"{annual_interest_rate}%",
            "appreciation": f"{expected_appreciation_percent}% per year",
            "rent_increase": f"{annual_rent_increase_percent}% per year",
            "maintenance": f"{MAINTENANCE_FEE_PERCENT}% of property value per year"
        },
        "years_analyzed": years_planning_to_stay
    }


def validate_user_eligibility(
    nationality: str,
    monthly_income: float,
    employment_type: str = "salaried",
    years_in_uae: float = 0
) -> dict:
    """
    Check basic eligibility for UAE mortgage.
    
    Args:
        nationality: "uae_national" or "expat"
        monthly_income: Gross monthly salary
        employment_type: "salaried", "self_employed", or "business_owner"
        years_in_uae: Years of UAE residency
    
    Returns:
        Eligibility status and requirements
    """
    issues = []
    warnings = []
    
    is_expat = nationality.lower() != "uae_national"
    max_ltv = MAX_LTV_EXPAT if is_expat else MAX_LTV_UAE_NATIONAL
    min_down_payment = (1 - max_ltv) * 100
    
    # Minimum income check (rough guideline: 15k AED for most banks)
    min_income = 15000 if is_expat else 10000
    if monthly_income < min_income:
        issues.append(f"Most banks require minimum income of {min_income:,} AED/month")
    
    # Self-employed restrictions
    if employment_type in ["self_employed", "business_owner"]:
        warnings.append("Self-employed applicants may face stricter documentation requirements (2+ years of audited accounts)")
        if is_expat and years_in_uae < 2:
            issues.append("Self-employed expats typically need 2+ years in UAE")
    
    # Residency for expats
    if is_expat and years_in_uae < 0.5:
        warnings.append("Some banks require 6+ months UAE residency")
    
    is_eligible = len(issues) == 0
    
    return {
        "is_eligible": is_eligible,
        "nationality_type": "Expat" if is_expat else "UAE National",
        "max_ltv": max_ltv * 100,
        "min_down_payment_percent": min_down_payment,
        "issues": issues,
        "warnings": warnings,
        "next_steps": [
            "Gather salary certificates (3 months)",
            "Prepare bank statements (6 months)",
            "Get Emirates ID copy",
            "Obtain passport copy with residence visa"
        ] if is_eligible else ["Address the issues listed above first"]
    }


# ============================================================================
# TOOL WRAPPERS FOR ADK AGENT (These are what the LLM calls)
# ============================================================================

def tool_calculate_mortgage(
    property_price: float,
    down_payment_percent: float = 20.0,
    interest_rate: float = 4.5,
    tenure_years: int = 25
) -> str:
    """
    Calculate mortgage EMI and total costs for a property in UAE.
    
    Use this whenever the user mentions a property price and wants to know
    the monthly payment or total cost.
    
    Args:
        property_price: The property price in AED (e.g., 2000000 for 2M)
        down_payment_percent: Down payment percentage, minimum 20% for expats
        interest_rate: Annual interest rate, default 4.5%
        tenure_years: Loan duration in years, maximum 25
    
    Returns:
        A formatted string with EMI details and warnings about upfront costs
    """
    emi = calculate_emi(property_price, down_payment_percent, interest_rate, tenure_years)
    upfront = calculate_upfront_costs(property_price, down_payment_percent)
    
    return f"""
📊 **Mortgage Calculation for {property_price:,.0f} AED Property**

**Monthly Payment (EMI):** {emi['monthly_emi']:,.0f} AED
**Loan Amount:** {emi['loan_amount']:,.0f} AED ({100 - down_payment_percent:.0f}% of property)
**Interest Rate:** {interest_rate}% per year
**Tenure:** {tenure_years} years ({emi['tenure_months']} months)

**Over {tenure_years} years, you'll pay:**
- Total Principal: {emi['loan_amount']:,.0f} AED
- Total Interest: {emi['total_interest']:,.0f} AED
- **Grand Total:** {emi['total_payment']:,.0f} AED

⚠️ **IMPORTANT: Upfront Cash Required**
{upfront['warning']}

**Breakdown of upfront costs:**
- Down Payment ({down_payment_percent:.0f}%): {upfront['down_payment']:,.0f} AED
- Transfer Fee (4% to DLD): {upfront['transfer_fee']:,.0f} AED
- Agency Fee (2%): {upfront['agency_fee']:,.0f} AED
- Misc Fees (1%): {upfront['misc_fees']:,.0f} AED
- **💰 Total Cash Needed:** {upfront['total_cash_needed']:,.0f} AED
"""


def tool_assess_affordability(
    monthly_income: float,
    existing_monthly_debts: float = 0,
    desired_property_price: float = 0
) -> str:
    """
    Assess how much property the user can afford based on their income.
    
    Use this when user mentions their income and wants to know what they can buy,
    or to verify if a specific property is within their budget.
    
    Args:
        monthly_income: User's gross monthly income in AED
        existing_monthly_debts: Other monthly payments (car loan, credit cards)
        desired_property_price: Optional - specific property to check affordability
    
    Returns:
        Affordability assessment with maximum budget and recommendations
    """
    result = calculate_affordability(monthly_income, 0, existing_monthly_debts)
    
    output = f"""
💰 **Affordability Assessment**

**Your Income:** {monthly_income:,.0f} AED/month
**Existing Debts:** {existing_monthly_debts:,.0f} AED/month
**Available for Mortgage:** {result['max_emi']:,.0f} AED/month (max)

**What you can afford:**
- Maximum Property: {result['max_property_price']:,.0f} AED
- Comfortable Budget: {result['comfortable_property_price']:,.0f} AED (recommended)
- Maximum Loan: {result['max_loan_amount']:,.0f} AED

**Debt-to-Income Ratio:** {result['dti_ratio']:.1f}%

{result['note']}
"""
    
    if desired_property_price > 0:
        is_affordable = desired_property_price <= result['max_property_price']
        is_comfortable = desired_property_price <= result['comfortable_property_price']
        
        if is_comfortable:
            output += f"\n✅ **{desired_property_price:,.0f} AED** is comfortably within your budget!"
        elif is_affordable:
            output += f"\n⚠️ **{desired_property_price:,.0f} AED** is possible but stretches your budget. Consider a lower price."
        else:
            gap = desired_property_price - result['max_property_price']
            output += f"\n❌ **{desired_property_price:,.0f} AED** exceeds your maximum by {gap:,.0f} AED."
    
    return output


def tool_compare_buy_vs_rent(
    property_price: float,
    monthly_rent: float,
    years_staying: int,
    down_payment_percent: float = 20.0
) -> str:
    """
    Compare buying vs continuing to rent, with detailed financial analysis.
    
    Use this when user wants to know if they should buy or keep renting.
    
    Args:
        property_price: Price of property they're considering in AED
        monthly_rent: Current monthly rent for similar property in AED
        years_staying: How many years they plan to stay in UAE
        down_payment_percent: How much they can put down (min 20%)
    
    Returns:
        Detailed buy vs rent comparison with clear recommendation
    """
    result = analyze_buy_vs_rent(
        property_price=property_price,
        current_monthly_rent=monthly_rent,
        years_planning_to_stay=years_staying,
        down_payment_percent=down_payment_percent
    )
    
    m = result['monthly_breakdown']
    c = result['cumulative_analysis']
    u = result['upfront_costs']
    
    return f"""
{result['reasoning']}

---

📊 **Monthly Cost Comparison**
| Buying | Renting |
|--------|---------|
| EMI: {m['mortgage_emi']:,.0f} AED | Rent: {m['current_monthly_rent']:,.0f} AED |
| Maintenance: {m['maintenance']:,.0f} AED | (included) |
| **Total: {m['total_monthly_buy_cost']:,.0f} AED** | **Total: {m['current_monthly_rent']:,.0f} AED** |

**Difference:** {m['difference']:+,.0f} AED/month ({"more" if m['difference'] > 0 else "less"} if buying)

---

📈 **{years_staying}-Year Analysis**

**If you BUY:**
- Upfront Cash Needed: {u['total_cash_needed']:,.0f} AED
- Total Payments: {c['total_buy_cost']:,.0f} AED
- Equity Built: {c['equity_buildup']:,.0f} AED
- **Net Position:** +{c['equity_buildup']:,.0f} AED in assets

**If you RENT:**
- Upfront Cost: 0 AED (just security deposit)
- Total Rent Paid: {c['total_rent_cost']:,.0f} AED
- Equity Built: 0 AED
- **Net Position:** -{c['total_rent_cost']:,.0f} AED (money gone)

**Break-even Point:** ~{c['break_even_years']} years

---

⚙️ **Assumptions Used:**
- Interest Rate: {result['assumptions']['interest_rate']}
- Property Appreciation: {result['assumptions']['appreciation']}
- Annual Rent Increase: {result['assumptions']['rent_increase']}
"""


def tool_check_eligibility(
    is_expat: bool = True,
    monthly_income: float = 0,
    is_self_employed: bool = False,
    years_in_uae: float = 1
) -> str:
    """
    Check if user is eligible for UAE mortgage.
    
    Use this to validate basic eligibility requirements.
    
    Args:
        is_expat: True if not UAE national
        monthly_income: Gross monthly income in AED
        is_self_employed: True if self-employed or business owner
        years_in_uae: Years of UAE residency
    
    Returns:
        Eligibility status with requirements and next steps
    """
    result = validate_user_eligibility(
        nationality="expat" if is_expat else "uae_national",
        monthly_income=monthly_income,
        employment_type="self_employed" if is_self_employed else "salaried",
        years_in_uae=years_in_uae
    )
    
    status = "✅ **You appear eligible for a UAE mortgage!**" if result['is_eligible'] else "⚠️ **There may be some challenges:**"
    
    output = f"""
{status}

**Your Profile:**
- Status: {result['nationality_type']}
- Maximum LTV: {result['max_ltv']:.0f}% (requires {result['min_down_payment_percent']:.0f}% down payment)
"""
    
    if result['issues']:
        output += "\n**Issues to Address:**\n"
        for issue in result['issues']:
            output += f"- ❌ {issue}\n"
    
    if result['warnings']:
        output += "\n**Things to Note:**\n"
        for warning in result['warnings']:
            output += f"- ⚠️ {warning}\n"
    
    if result['is_eligible']:
        output += "\n**Documents You'll Need:**\n"
        for step in result['next_steps']:
            output += f"- {step}\n"
    
    return output


def tool_get_uae_mortgage_rules() -> str:
    """
    Get the key UAE mortgage rules and constraints.
    
    Use this to educate users about UAE mortgage regulations.
    
    Returns:
        Summary of key UAE mortgage rules
    """
    return f"""
📋 **UAE Mortgage Rules for Expats (Key Facts)**

**1. Loan-to-Value (LTV) Limits:**
- Expats: Maximum **80% LTV** (20% down payment required)
- UAE Nationals: Maximum 85% LTV
- For properties under 5M AED (most common)

**2. Maximum Tenure:**
- **25 years maximum**
- Must be repaid before age 65-70 (depends on bank)

**3. Upfront Costs (The Hidden ~7%):**
- **4%**: Dubai Land Department Transfer Fee
- **2%**: Real Estate Agent Commission  
- **1%**: Valuation, Mortgage Registration, Insurance
- Total: You need **27%+ cash** (20% down + 7% fees)

**4. Current Interest Rates:**
- Standard market rate: ~**{DEFAULT_INTEREST_RATE}%** per annum
- Rates are typically variable (linked to EIBOR)

**5. Eligibility Requirements:**
- Minimum income: ~15,000 AED/month (most banks)
- Maximum debt-to-income: Usually 50%
- Required documents: Salary certificate, bank statements, Emirates ID

**6. Buy vs Rent Rule of Thumb:**
- Staying < 3 years? **Rent** (fees will eat profits)
- Staying > 5 years? **Consider buying** (equity buildup)

💡 These rules are enforced in all my calculations to ensure accuracy.
"""
