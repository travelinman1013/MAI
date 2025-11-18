import pytest
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel
from src.core.agents.base import BaseAgentFramework, AgentDependencies
from src.core.models.responses import StandardResponse

class AnalysisData(BaseModel):
    topic: str
    keywords: list[str]

# Define the expected result type
AnalysisResult = StandardResponse[AnalysisData]

class AnalysisAgent(BaseAgentFramework[AnalysisResult]):
    def __init__(self, model):
        super().__init__(
            name="analyst",
            model=model,
            result_type=AnalysisResult,
            system_prompt="Analyze the input.",
        )

@pytest.mark.asyncio
async def test_agent_structured_output():
    # Create a TestModel that returns a valid JSON matching the schema
    # Note: TestModel in Pydantic AI usually returns the raw text which the agent then parses.
    # We need to provide a JSON string that matches StandardResponse[AnalysisData]
    
    expected_data = {
        "data": {
            "topic": "AI Frameworks",
            "keywords": ["agents", "memory", "tools"]
        },
        "confidence_score": 0.9,
        "reasoning": "Input mentioned AI components."
    }
    
    model = TestModel(custom_output_args=expected_data)
    
    agent = AnalysisAgent(model)
    deps = AgentDependencies()
    
    result = await agent.run_async("Analyze AI frameworks", deps=deps)
    
    assert isinstance(result, StandardResponse)
    assert result.data.topic == "AI Frameworks"
    assert result.data.keywords == ["agents", "memory", "tools"]
    assert result.confidence_score == 0.9
    assert result.reasoning == "Input mentioned AI components."

@pytest.mark.asyncio
async def test_agent_validation_retry_on_bad_json():
    # Test that the agent (via Pydantic AI) handles bad JSON by retrying 
    # (TestModel simulates retries by taking a list of responses or a function)
    
    # For this test, we'll just check if it raises or handles a completely invalid response if retries run out
    # We provide args that don't match the schema (missing fields)
    
    model = TestModel(custom_output_args={"data": "invalid_structure"})
    
    agent = AnalysisAgent(model)
    deps = AgentDependencies()
    
    # It should raise AgentExecutionError (wrapping Pydantic AI's error)
    from src.core.utils.exceptions import AgentExecutionError
    
    with pytest.raises(AgentExecutionError):
        await agent.run_async("Analyze", deps=deps)