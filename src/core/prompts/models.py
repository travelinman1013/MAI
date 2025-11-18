from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class PromptTemplate(BaseModel):
    """
    Pydantic model for a prompt template.
    Defines the structure of a YAML-based prompt.
    """
    name: str = Field(..., description="Unique name for the prompt template")
    version: str = Field("1.0.0", description="Version of the prompt template")
    template: str = Field(..., description="The Jinja2 template string for the prompt")
    description: Optional[str] = Field(None, description="A brief description of the prompt's purpose")
    input_variables: Dict[str, Any] = Field(default_factory=dict, description="Expected input variables and their types/defaults")
    output_variables: Dict[str, Any] = Field(default_factory=dict, description="Expected output structure or variables")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary metadata")
