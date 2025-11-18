import pytest
from pydantic import BaseModel
from src.core.models.responses import StandardResponse, ChatResponse, ErrorResponse
from datetime import datetime

class SimpleData(BaseModel):
    count: int
    items: list[str]

def test_standard_response_structure():
    data = SimpleData(count=2, items=["a", "b"])
    response = StandardResponse[SimpleData](
        data=data,
        reasoning="Counted items",
        confidence_score=0.95
    )
    
    assert response.data.count == 2
    assert response.data.items == ["a", "b"]
    assert response.reasoning == "Counted items"
    assert response.confidence_score == 0.95
    assert isinstance(response.timestamp, datetime)
    assert response.metadata == {}

def test_chat_response_structure():
    response = ChatResponse(content="Hello world", role="assistant")
    assert response.content == "Hello world"
    assert response.role == "assistant"

def test_error_response_structure():
    response = ErrorResponse(
        error_code="TEST_ERROR",
        message="Something went wrong",
        details={"info": "details"}
    )
    assert response.error_code == "TEST_ERROR"
    assert response.message == "Something went wrong"
    assert response.details["info"] == "details"
