"""
Tests for the Mortgage Agent configuration and behavior.
"""

import pytest
from mortgage_agent.agent import (
    root_agent,
    load_system_prompt,
    MORTGAGE_TOOLS,
)


class TestAgentConfiguration:
    """Test agent setup and configuration."""
    
    def test_system_prompt_loads(self):
        """Test that system prompt file loads correctly."""
        prompt = load_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "ramy" in prompt.lower() or "advisor" in prompt.lower()
    
    def test_system_prompt_contains_key_instructions(self):
        """Test that system prompt has essential instructions."""
        prompt = load_system_prompt()
        
        # Should mention tools
        assert "tool" in prompt.lower()
        
        # Should mention not guessing numbers
        assert "calculate" in prompt.lower() or "guess" in prompt.lower()
        
        # Should have personality guidance
        assert "friendly" in prompt.lower() or "warm" in prompt.lower() or "empathy" in prompt.lower()
    
    def test_tools_are_defined(self):
        """Test that all required tools are defined."""
        tool_names = [t["name"] for t in MORTGAGE_TOOLS]
        
        assert "tool_calculate_mortgage" in tool_names
        assert "tool_assess_affordability" in tool_names
        assert "tool_compare_buy_vs_rent" in tool_names
        assert "tool_check_eligibility" in tool_names
        assert "tool_get_uae_mortgage_rules" in tool_names
    
    def test_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        for tool in MORTGAGE_TOOLS:
            assert "description" in tool
            assert len(tool["description"]) > 20
    
    def test_tools_have_parameters(self):
        """Test that tools have parameter definitions."""
        for tool in MORTGAGE_TOOLS:
            assert "parameters" in tool
            assert "required" in tool
    
    def test_agent_exists(self):
        """Test that root agent is created successfully."""
        assert root_agent is not None
        # Agent should be an ADK Agent with name attribute
        assert hasattr(root_agent, "name")
        assert root_agent.name == "mortgage_advisor"


class TestToolSchemas:
    """Test tool schema definitions are valid."""
    
    def test_calculate_mortgage_schema(self):
        """Test mortgage calculation tool schema."""
        tool = next(t for t in MORTGAGE_TOOLS if t["name"] == "tool_calculate_mortgage")
        
        assert "property_price" in tool["parameters"]
        assert tool["parameters"]["property_price"]["type"] == "number"
        assert "property_price" in tool["required"]
    
    def test_affordability_schema(self):
        """Test affordability tool schema."""
        tool = next(t for t in MORTGAGE_TOOLS if t["name"] == "tool_assess_affordability")
        
        assert "monthly_income" in tool["parameters"]
        assert "monthly_income" in tool["required"]
    
    def test_buy_vs_rent_schema(self):
        """Test buy vs rent tool schema."""
        tool = next(t for t in MORTGAGE_TOOLS if t["name"] == "tool_compare_buy_vs_rent")
        
        assert "property_price" in tool["parameters"]
        assert "monthly_rent" in tool["parameters"]
        assert "years_staying" in tool["parameters"]
        assert len(tool["required"]) == 3
    
    def test_eligibility_schema(self):
        """Test eligibility tool schema."""
        tool = next(t for t in MORTGAGE_TOOLS if t["name"] == "tool_check_eligibility")
        
        assert "is_expat" in tool["parameters"]
        assert tool["parameters"]["is_expat"]["type"] == "boolean"
    
    def test_rules_tool_has_no_required_params(self):
        """Test that rules tool doesn't require parameters."""
        tool = next(t for t in MORTGAGE_TOOLS if t["name"] == "tool_get_uae_mortgage_rules")
        
        assert tool["required"] == []


class TestAgentBehaviorGuidelines:
    """Test that agent has proper behavioral guidelines."""
    
    def test_prompt_prevents_hallucination(self):
        """Test that prompt explicitly prevents math hallucination."""
        prompt = load_system_prompt()
        prompt_lower = prompt.lower()
        
        # Should have explicit instructions about using tools for math
        has_tool_instruction = (
            "always use" in prompt_lower or
            "never estimate" in prompt_lower or
            "never guess" in prompt_lower or
            "must use" in prompt_lower
        )
        assert has_tool_instruction
    
    def test_prompt_mentions_upfront_costs(self):
        """Test that prompt emphasizes hidden costs."""
        prompt = load_system_prompt()
        prompt_lower = prompt.lower()
        
        # Should mention the hidden costs/fees
        has_fee_warning = (
            "7%" in prompt or
            "hidden" in prompt_lower or
            "upfront" in prompt_lower or
            "transfer fee" in prompt_lower
        )
        assert has_fee_warning
    
    def test_prompt_has_lead_capture_guidance(self):
        """Test that prompt includes lead capture instructions."""
        prompt = load_system_prompt()
        prompt_lower = prompt.lower()
        
        # Should have guidance on collecting contact info
        has_lead_guidance = (
            "email" in prompt_lower or
            "contact" in prompt_lower or
            "lead" in prompt_lower
        )
        assert has_lead_guidance


class TestModularity:
    """Test that the architecture is modular and pluggable."""
    
    def test_tools_are_standalone_functions(self):
        """Test that tools can be called independently."""
        from mortgage_agent.tools import tool_calculate_mortgage
        
        # Should work without any agent context
        result = tool_calculate_mortgage(property_price=1_000_000)
        assert isinstance(result, str)
        assert "AED" in result
    
    def test_agent_has_tools_registered(self):
        """Test that agent has tools registered."""
        # The agent should have tools
        assert hasattr(root_agent, "tools")
        assert len(root_agent.tools) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

