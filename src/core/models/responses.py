from typing import Optional, Generic, TypeVar, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

DataT = TypeVar("DataT")

class BaseResponse(BaseModel):
    """
    Base model for all structured responses from agents.
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="Time of response generation")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of the agent (0-1)")
    reasoning: Optional[str] = Field(default=None, description="Optional reasoning or thought process")

class StandardResponse(BaseResponse, Generic[DataT]):
    """
    Standardized envelope for agent responses.
    
    Usage:
        class MyData(BaseModel):
            summary: str
            items: list[str]
            
        response = StandardResponse[MyData](
            data=MyData(...),
            reasoning="I analyzed the input..."
        )
    """
    data: DataT = Field(description="The structured payload of the response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ErrorResponse(BaseResponse):
    """
    Standardized error response.
    """
    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")

class ChatResponse(BaseResponse):
    """
    Simple response for chat interactions.
    """
    content: str = Field(description="The textual response content")
    role: str = Field(default="assistant", description="The role of the responder")
