"""
Tests for Mortgage Calculation Tools.

These tests ensure the deterministic functions produce correct results,
which is critical because LLMs must never guess these numbers.
"""

import pytest
import math
from mortgage_agent.tools import (
    calculate_emi,
    calculate_upfront_costs,
    calculate_affordability,
    analyze_buy_vs_rent,
    validate_user_eligibility,
    tool_calculate_mortgage,
    tool_assess_affordability,
    tool_compare_buy_vs_rent,
    tool_check_eligibility,
    tool_get_uae_mortgage_rules,
    MAX_LTV_EXPAT,
    DEFAULT_INTEREST_RATE,
    MAX_TENURE_YEARS,
    TOTAL_UPFRONT_COSTS_PERCENT,
)


class TestEMICalculation:
    """Test the core EMI calculation function."""
    
    def test_basic_emi_calculation(self):
        """Test EMI calculation with standard inputs."""
        result = calculate_emi(
            property_price=2_000_000,
            down_payment_percent=20.0,
            annual_interest_rate=4.5,
            tenure_years=25
        )
        
        # Verify loan amount
        assert result["loan_amount"] == 1_600_000.0
        assert result["down_payment"] == 400_000.0
        
        # EMI should be around 8,900 AED for this scenario
        assert 8_800 < result["monthly_emi"] < 9_000
        
        # Total payment over 25 years
        assert result["tenure_months"] == 300
        assert result["total_payment"] > result["loan_amount"]
    
    def test_minimum_down_payment_enforced(self):
        """Test that 20% minimum is enforced for expats."""
        result = calculate_emi(
            property_price=1_000_000,
            down_payment_percent=10.0,  # Below minimum
            annual_interest_rate=4.5,
            tenure_years=25
        )
        
        # Should be calculated with 20% down, not 10%
        assert result["down_payment"] == 200_000.0
        assert result["loan_amount"] == 800_000.0
    
    def test_max_tenure_enforced(self):
        """Test that 25 year maximum is enforced."""
        result = calculate_emi(
            property_price=1_000_000,
            down_payment_percent=20.0,
            annual_interest_rate=4.5,
            tenure_years=35  # Above maximum
        )
        
        assert result["tenure_years"] == MAX_TENURE_YEARS
        assert result["tenure_months"] == MAX_TENURE_YEARS * 12
    
    def test_known_emi_value(self):
        """Test against a known EMI calculation."""
        # For 1,000,000 loan at 4.5% for 25 years, EMI should be ~5,559 AED
        result = calculate_emi(
            property_price=1_250_000,
            down_payment_percent=20.0,
            annual_interest_rate=4.5,
            tenure_years=25
        )
        
        # 1,250,000 * 0.8 = 1,000,000 loan
        assert result["loan_amount"] == 1_000_000.0
        assert abs(result["monthly_emi"] - 5559) < 10  # Within 10 AED


class TestUpfrontCosts:
    """Test upfront cost calculations."""
    
    def test_upfront_costs_breakdown(self):
        """Test that all fees are calculated correctly."""
        result = calculate_upfront_costs(
            property_price=2_000_000,
            down_payment_percent=20.0
        )
        
        # Down payment: 20% of 2M = 400,000
        assert result["down_payment"] == 400_000.0
        
        # Transfer fee: 4% of 2M = 80,000
        assert result["transfer_fee"] == 80_000.0
        
        # Agency fee: 2% of 2M = 40,000
        assert result["agency_fee"] == 40_000.0
        
        # Misc fees: 1% of 2M = 20,000
        assert result["misc_fees"] == 20_000.0
        
        # Total fees: 7% = 140,000
        assert result["total_fees"] == 140_000.0
        
        # Total cash needed: 400,000 + 140,000 = 540,000
        assert result["total_cash_needed"] == 540_000.0
    
    def test_minimum_down_payment_enforced(self):
        """Test that 20% minimum is enforced."""
        result = calculate_upfront_costs(
            property_price=1_000_000,
            down_payment_percent=15.0
        )
        
        # Should use 20%, not 15%
        assert result["down_payment"] == 200_000.0
        assert result["down_payment_percent"] == 20.0


class TestAffordability:
    """Test affordability calculation."""
    
    def test_basic_affordability(self):
        """Test affordability with standard income."""
        result = calculate_affordability(
            monthly_income=30_000,
            monthly_expenses=10_000,
            existing_debts=0
        )
        
        assert result["is_affordable"] == True
        assert result["max_emi"] == 15_000.0  # 50% of 30,000
        assert result["recommended_emi"] == 10_500.0  # 70% of max
        assert result["max_property_price"] > 0
    
    def test_high_existing_debt(self):
        """Test when existing debts consume available income."""
        result = calculate_affordability(
            monthly_income=20_000,
            monthly_expenses=5_000,
            existing_debts=15_000  # Already at 75% DTI
        )
        
        # 50% of 20k = 10k for debts, but 15k already owed
        assert result["is_affordable"] == False
        assert "warning" in result
    
    def test_dti_calculation(self):
        """Test debt-to-income ratio calculation."""
        result = calculate_affordability(
            monthly_income=40_000,
            monthly_expenses=0,
            existing_debts=5_000,
            max_dti_ratio=50.0
        )
        
        # Max mortgage payment = 50% of 40k - 5k = 15k
        assert result["max_emi"] == 15_000.0


class TestBuyVsRent:
    """Test buy vs rent analysis."""
    
    def test_short_stay_recommends_rent(self):
        """Test that < 3 years recommends renting."""
        result = analyze_buy_vs_rent(
            property_price=2_000_000,
            current_monthly_rent=8_000,
            years_planning_to_stay=2
        )
        
        assert result["recommendation"] == "RENT"
        assert "transaction" in result["reasoning"].lower() or "rent" in result["reasoning"].lower()
    
    def test_long_stay_recommends_buy(self):
        """Test that > 5 years recommends buying."""
        result = analyze_buy_vs_rent(
            property_price=2_000_000,
            current_monthly_rent=12_000,  # High rent
            years_planning_to_stay=10
        )
        
        assert result["recommendation"] == "BUY"
        assert result["cumulative_analysis"]["equity_buildup"] > 0
    
    def test_monthly_breakdown_included(self):
        """Test that monthly costs are calculated."""
        result = analyze_buy_vs_rent(
            property_price=1_500_000,
            current_monthly_rent=6_000,
            years_planning_to_stay=5
        )
        
        mb = result["monthly_breakdown"]
        assert "mortgage_emi" in mb
        assert "maintenance" in mb
        assert "total_monthly_buy_cost" in mb
        assert "current_monthly_rent" in mb
    
    def test_break_even_calculated(self):
        """Test break-even point calculation."""
        result = analyze_buy_vs_rent(
            property_price=2_000_000,
            current_monthly_rent=10_000,
            years_planning_to_stay=7
        )
        
        assert result["cumulative_analysis"]["break_even_years"] > 0
        assert result["cumulative_analysis"]["break_even_years"] < 99


class TestEligibility:
    """Test eligibility validation."""
    
    def test_expat_ltv_limit(self):
        """Test expat LTV is set to 80%."""
        result = validate_user_eligibility(
            nationality="expat",
            monthly_income=30_000
        )
        
        assert result["max_ltv"] == 80.0
        assert abs(result["min_down_payment_percent"] - 20.0) < 0.001
    
    def test_low_income_warning(self):
        """Test low income is flagged."""
        result = validate_user_eligibility(
            nationality="expat",
            monthly_income=10_000
        )
        
        assert result["is_eligible"] == False
        assert len(result["issues"]) > 0
    
    def test_self_employed_warning(self):
        """Test self-employed gets warnings."""
        result = validate_user_eligibility(
            nationality="expat",
            monthly_income=50_000,
            employment_type="self_employed",
            years_in_uae=3
        )
        
        assert len(result["warnings"]) > 0


class TestToolWrappers:
    """Test the tool wrapper functions that the LLM calls."""
    
    def test_tool_calculate_mortgage_returns_string(self):
        """Tool wrappers must return strings for LLM consumption."""
        result = tool_calculate_mortgage(
            property_price=2_000_000,
            down_payment_percent=20.0
        )
        
        assert isinstance(result, str)
        assert "monthly" in result.lower() or "emi" in result.lower()
        assert "aed" in result.lower()
    
    def test_tool_assess_affordability_returns_string(self):
        """Test affordability tool returns formatted string."""
        result = tool_assess_affordability(
            monthly_income=25_000,
            existing_monthly_debts=3_000
        )
        
        assert isinstance(result, str)
        assert "afford" in result.lower()
    
    def test_tool_compare_buy_vs_rent_returns_string(self):
        """Test buy vs rent tool returns formatted string."""
        result = tool_compare_buy_vs_rent(
            property_price=1_500_000,
            monthly_rent=7_000,
            years_staying=5
        )
        
        assert isinstance(result, str)
        assert "buy" in result.lower() or "rent" in result.lower()
    
    def test_tool_check_eligibility_returns_string(self):
        """Test eligibility tool returns formatted string."""
        result = tool_check_eligibility(
            is_expat=True,
            monthly_income=30_000
        )
        
        assert isinstance(result, str)
        assert "eligible" in result.lower() or "ltv" in result.lower()
    
    def test_tool_get_uae_mortgage_rules_returns_string(self):
        """Test rules tool returns formatted string."""
        result = tool_get_uae_mortgage_rules()
        
        assert isinstance(result, str)
        assert "80%" in result  # LTV limit
        assert "4%" in result  # Transfer fee
        assert "25" in result  # Max tenure


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_income(self):
        """Test handling of zero income."""
        result = calculate_affordability(
            monthly_income=0,
            monthly_expenses=0,
            existing_debts=0
        )
        
        assert result["is_affordable"] == False
    
    def test_very_high_property_price(self):
        """Test calculation with luxury property."""
        result = calculate_emi(
            property_price=50_000_000,
            down_payment_percent=30.0,
            annual_interest_rate=4.5,
            tenure_years=25
        )
        
        # Should still calculate correctly
        assert result["loan_amount"] == 35_000_000.0
        assert result["monthly_emi"] > 0
    
    def test_minimum_property_price(self):
        """Test with minimum viable property price."""
        result = calculate_emi(
            property_price=500_000,
            down_payment_percent=20.0,
            annual_interest_rate=4.5,
            tenure_years=25
        )
        
        assert result["monthly_emi"] > 0
        assert result["loan_amount"] == 400_000.0
    
    def test_short_tenure(self):
        """Test with very short tenure."""
        result = calculate_emi(
            property_price=1_000_000,
            down_payment_percent=20.0,
            annual_interest_rate=4.5,
            tenure_years=5
        )
        
        assert result["tenure_years"] == 5
        # Shorter tenure = higher EMI
        assert result["monthly_emi"] > 10_000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
