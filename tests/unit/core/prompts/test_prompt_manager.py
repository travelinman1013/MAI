import pytest
import os
import shutil
import yaml
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.core.prompts.models import PromptTemplate
from src.core.prompts.registry import PromptManager, SecureSandbox
from src.core.utils.exceptions import ConfigurationError, ResourceNotFoundError, ValidationError, MAIException


# --- Fixtures ---

@pytest.fixture
def temp_prompt_dir(tmp_path):
    """Creates a temporary directory for prompt YAML files."""
    test_dir = tmp_path / "test_prompts"
    test_dir.mkdir()
    (test_dir / "base").mkdir()
    (test_dir / "agents").mkdir()
    return test_dir

@pytest.fixture
def create_mock_yaml(temp_prompt_dir):
    """Helper to create mock YAML files for prompts."""
    def _creator(
        name: str,
        template_content: str,
        version: str = "1.0.0",
        description: Optional[str] = None,
        input_variables: Optional[dict] = None,
        output_variables: Optional[dict] = None,
        tags: Optional[list] = None,
        metadata: Optional[dict] = None,
        sub_dir: str = "base"
    ):
        prompt_data = {
            "name": name,
            "version": version,
            "template": template_content, # yaml.dump will handle this as a literal string
        }
        if description: prompt_data["description"] = description
        if input_variables: prompt_data["input_variables"] = input_variables
        if output_variables: prompt_data["output_variables"] = output_variables
        if tags: prompt_data["tags"] = tags
        if metadata: prompt_data["metadata"] = metadata

        # Generate a unique filename that includes version
        filename_name = name.replace("/", "_") # Replace slashes for filename safety
        file_path = temp_prompt_dir / sub_dir / f"{filename_name}_v{version}.yaml"
        with open(file_path, "w") as f:
            yaml.dump(prompt_data, f)
        return file_path
    return _creator

@pytest.fixture
def prompt_manager(temp_prompt_dir, create_mock_yaml):
    """Initializes and returns a PromptManager instance."""
    # Ensure PromptManager is re-initialized for each test to avoid singleton state issues
    PromptManager._instance = None
    PromptManager._is_initialized = False

    # Create a default system prompt
    create_mock_yaml(
        name="system_prompt",
        template_content="Hello, {{ name }}. Current time: {{ current_time }}.",
        input_variables={"name": {"type": "string", "default": "User", "required": False}, "current_time": {"type": "string", "required": True}},
        sub_dir="base"
    )
    # Create another prompt with a different version
    create_mock_yaml(
        name="system_prompt",
        template_content="Hello, {{ name }}. It is now {{ current_time }}.",
        version="2.0.0",
        input_variables={"name": {"type": "string", "default": "User"}, "current_time": {"type": "string", "required": True}},
        sub_dir="base"
    )
    # Create an agent specific prompt
    create_mock_yaml(
        name="agent_persona",
        template_content="You are a {{ role }}. Your goal is to {{ goal }}.",
        input_variables={"role": {"type": "string"}, "goal": {"type": "string"}},
        sub_dir="agents"
    )
    # Create prompt for Jinja2 error test
    create_mock_yaml(
        name="bad_syntax",
        template_content="Hello {{ undefined_var }}", # Valid YAML, but will cause Jinja2 UndefinedError
        input_variables={"something": {"type": "boolean"}},
        sub_dir="base"
    )
    # Create prompts for sandboxing tests
    create_mock_yaml(
        name="malicious_prompt",
        template_content="{{ ''.__class__.__mro__[1].__subclasses__() }}",
        sub_dir="base"
    )
    create_mock_yaml(
        name="malicious_prompt_globals",
        template_content="{{ config.__class__ }}", # Accessing __class__ should be blocked
        input_variables={"config": {"type": "dict"}},
        sub_dir="base"
    )
    create_mock_yaml(
        name="malicious_prompt_dot_access",
        template_content="{{ config.SECRET_KEY }}", # Dot access for items should be blocked on dicts
        input_variables={"config": {"type": "dict"}},
        sub_dir="base"
    )
    create_mock_yaml(
        name="safe_globals",
        template_content="{% for i in range(3) %}{{ i }}{% endfor %}",
        sub_dir="base"
    )

    manager = PromptManager(prompt_dir=str(temp_prompt_dir))
    return manager

    manager = PromptManager(prompt_dir=str(temp_prompt_dir))
    return manager

# --- Test Cases for PromptTemplate Model ---

def test_prompt_template_model_valid():
    data = {
        "name": "test_prompt",
        "template": "Hello, {{ name }}!",
        "version": "1.0.0",
        "input_variables": {"name": {"type": "string"}},
        "tags": ["greeting"]
    }
    template = PromptTemplate(**data)
    assert template.name == "test_prompt"
    assert template.template == "Hello, {{ name }}!"
    assert template.version == "1.0.0"
    assert "name" in template.input_variables
    assert "greeting" in template.tags

def test_prompt_template_model_defaults():
    data = {
        "name": "default_prompt",
        "template": "Just a template."
    }
    template = PromptTemplate(**data)
    assert template.version == "1.0.0"
    assert template.input_variables == {}
    assert template.tags == []

def test_prompt_template_model_missing_required_fields():
    with pytest.raises(ValueError, match="Field required"):
        PromptTemplate(name="missing_template")
    with pytest.raises(ValueError, match="Field required"):
        PromptTemplate(template="missing_name")

# --- Test Cases for PromptManager ---

def test_prompt_manager_singleton(prompt_manager):
    manager1 = prompt_manager
    manager2 = PromptManager(prompt_dir="some/other/path") # Should return the same instance
    assert manager1 is manager2
    assert manager1.prompt_dir == str(prompt_manager.prompt_dir) # Check it wasn't re-initialized with new path

def test_prompt_manager_initialization_loads_prompts(prompt_manager):
    assert len(prompt_manager.templates) == 8 # Now loads 8 templates
    assert ("system_prompt", "1.0.0") in prompt_manager.templates
    assert ("system_prompt", "2.0.0") in prompt_manager.templates
    assert ("agent_persona", "1.0.0") in prompt_manager.templates

def test_prompt_manager_init_non_existent_dir():
    PromptManager._instance = None
    PromptManager._is_initialized = False
    with pytest.raises(ConfigurationError, match="Prompt directory not found"):
        PromptManager(prompt_dir="non_existent_dir")

def test_get_template_success(prompt_manager):
    template = prompt_manager.get_template("system_prompt", "1.0.0")
    assert template.name == "system_prompt"
    assert template.version == "1.0.0"
    assert "Hello, {{ name }}" in template.template

def test_get_template_different_version(prompt_manager):
    template = prompt_manager.get_template("system_prompt", "2.0.0")
    assert template.name == "system_prompt"
    assert template.version == "2.0.0"
    assert "It is now {{ current_time }}" in template.template

def test_get_template_not_found(prompt_manager):
    with pytest.raises(ResourceNotFoundError, match="Prompt template 'non_existent' version '1.0.0' not found."):
        prompt_manager.get_template("non_existent")

def test_get_template_reloads_on_not_found(temp_prompt_dir, prompt_manager, create_mock_yaml):
    # Manager is initialized, templates are loaded
    assert ("new_prompt", "1.0.0") not in prompt_manager.templates

    # Add a new prompt after manager is initialized
    create_mock_yaml(name="new_prompt", template_content="New content", sub_dir="base")

    # The current implementation of get_template calls _load_prompts if template not found
    reloaded_template = prompt_manager.get_template("new_prompt") # This call will trigger reload and succeed
    assert reloaded_template.name == "new_prompt"
    assert ("new_prompt", "1.0.0") in prompt_manager.templates
    assert prompt_manager.templates[("new_prompt", "1.0.0")][0] == reloaded_template # Access the PromptTemplate model from the stored tuple

def test_render_template_success(prompt_manager):
    rendered = prompt_manager.render_template(
        prompt_name="system_prompt", 
        prompt_version="1.0.0", 
        name="World", # This is the template variable 'name'
        current_time=datetime.now().strftime("%H:%M")
    )
    assert "Hello, World." in rendered
    assert datetime.now().strftime("%H:%M") in rendered

def test_render_template_with_default_value(prompt_manager):
    rendered = prompt_manager.render_template(
        prompt_name="system_prompt", 
        prompt_version="1.0.0", 
        current_time="12:00"
    )
    assert "Hello, User." in rendered # Uses default for 'name'
    assert "Current time: 12:00." in rendered

def test_render_template_missing_required_variable(prompt_manager):
    with pytest.raises(ValidationError, match="Missing required input variables for prompt 'system_prompt' v1.0.0: current_time"):
        prompt_manager.render_template(
            prompt_name="system_prompt", 
            prompt_version="1.0.0", 
            name="Tester"
        )

def test_render_template_jinja2_error(prompt_manager):

    try:
        prompt_manager.render_template(prompt_name="bad_syntax", something=True)
        pytest.fail("MAIException was not raised for Jinja2 error.")
    except MAIException as excinfo:
        assert excinfo.error_code == "PROMPT_RENDER_ERROR"
        assert "Error rendering prompt 'bad_syntax' v1.0.0" in excinfo.message
        assert "'undefined_var' is undefined" in excinfo.message

def test_render_template_sandboxing(prompt_manager):
    # Test for attempts to access unsafe attributes
    with pytest.raises(MAIException) as excinfo:
        prompt_manager.render_template(prompt_name="malicious_prompt")
    assert excinfo.value.error_code == "PROMPT_RENDER_ERROR"
    assert "access to attribute '__mro__' of 'type' object is unsafe" in excinfo.value.message

    with pytest.raises(MAIException) as excinfo_globals:
        prompt_manager.render_template(prompt_name="malicious_prompt_globals", config={"SECRET_KEY": "super_secret"})
    assert excinfo_globals.value.error_code == "PROMPT_RENDER_ERROR"
    # We expect __class__ access to be blocked.
    # The exact error message from Jinja2 might vary but usually says "access to attribute '__class__' of 'dict' object is unsafe"
    # or "attribute '__class__' is not defined" if we completely hide it.
    # With SecureSandbox returning False for is_safe_attribute(dict, ...), it should raise SecurityError.
    assert "access to attribute '__class__' of 'dict' object is unsafe" in excinfo_globals.value.message
    
    # Test dot access to dict items (should be blocked by strict getattr)
    with pytest.raises(MAIException) as excinfo_dot:
        prompt_manager.render_template(prompt_name="malicious_prompt_dot_access", config={"SECRET_KEY": "super_secret"})
    assert excinfo_dot.value.error_code == "PROMPT_RENDER_ERROR"
    assert "access to attribute 'SECRET_KEY' of 'dict' object is unsafe" in excinfo_dot.value.message

    # Test access to allowed globals (e.g., range)
    rendered = prompt_manager.render_template(prompt_name="safe_globals")
    assert rendered.strip() == "012"

def test_reload_prompts(prompt_manager, create_mock_yaml):
    initial_template_count = len(prompt_manager.templates)
    
    # Add a new prompt after initial load
    create_mock_yaml(name="new_prompt_after_load", template_content="New one.", sub_dir="base")
    assert ("new_prompt_after_load", "1.0.0") not in prompt_manager.templates
    
    prompt_manager.reload_prompts()
    
    assert len(prompt_manager.templates) == initial_template_count + 1
    assert ("new_prompt_after_load", "1.0.0") in prompt_manager.templates
    
    # Check if caches were cleared and then refilled
    prompt_manager.get_template.cache_info().hits == 0

def test_prompt_manager_name_from_filepath(temp_prompt_dir, create_mock_yaml):
    # Create a YAML without explicit name field
    file_path = temp_prompt_dir / "agents" / "planner_v3.yaml"
    with open(file_path, "w") as f:
        yaml.dump({
            "template": "I am a {{ agent_type }}",
            "version": "3.0.0",
            "input_variables": {"agent_type": {"type": "string"}}
        }, f)
    
    PromptManager._instance = None
    PromptManager._is_initialized = False
    manager = PromptManager(prompt_dir=str(temp_prompt_dir))
    
    template = manager.get_template("agents/planner_v3", "3.0.0")
    assert template.name == "agents/planner_v3"
    assert "I am a {{ agent_type }}" in template.template
    assert "3.0.0" == template.version
    rendered = manager.render_template(prompt_name="agents/planner_v3", prompt_version="3.0.0", agent_type="planner")
    assert rendered.strip() == "I am a planner"
