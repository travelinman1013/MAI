import os
import re
import yaml
from typing import Dict, Optional, Any, Tuple
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, Template, StrictUndefined
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import Template

from src.core.prompts.models import PromptTemplate
from src.core.utils.logging import logger
from src.core.utils.exceptions import ConfigurationError, ValidationError, MAIException, ResourceNotFoundError


# Define a stricter sandbox for Jinja2 to prevent template injection
class SecureSandbox(SandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, insecure_call=None):
        # Explicitly control attribute access on dictionaries for security
        if isinstance(obj, dict):
            # Allow only a very limited set of safe methods on dicts if needed
            if attr in ['get', 'keys', 'values', 'items', '__len__', '__str__', '__repr__']:
                return True
            return False # Disallow all other attribute access on dicts
        
        # Allow access to common safe attributes/methods for non-dict objects
        if attr in ['__str__', '__repr__', '__len__', 'get', 'items', 'values', 'keys', 'split', 'join', 'strip', 'lower', 'upper', 'replace', 'find', 'count', 'startswith', 'endswith', 'isdigit', 'isalpha', 'isalnum', 'format']:
            return True
        
        # Allow access to built-in types methods generally considered safe
        if isinstance(obj, (str, int, float, bool, type(None))):
            return True
        
        # Prevent access to all unsafe magic methods and dunder attributes
        if attr.startswith('__'):
            return False
        
        return super().is_safe_attribute(obj, attr, insecure_call)

    def getattr(self, obj, attribute):
        """
        Overrides default getattr to strictly enforce is_safe_attribute on dictionaries
        and prevent fallback to item lookup for dot notation if the attribute is unsafe.
        """
        if isinstance(obj, dict):
            # For dicts, strict check: if it's not a safe attribute, block it.
            # This prevents `dict.key` access if `key` is not a safe attribute.
            # We want to force users to use `dict['key']` or `dict.get('key')`.
            if not self.is_safe_attribute(obj, attribute, obj):
                return self.unsafe_undefined(obj, attribute)
            
            # If it IS a safe attribute (like .keys, .items), get it.
            try:
                return getattr(obj, attribute)
            except AttributeError:
                # Should not happen if is_safe_attribute is correct, but just in case
                return self.undefined(obj=obj, name=attribute)
        
        # For non-dict objects, use standard behavior (which might fallback to item lookup depending on object)
        return super().getattr(obj, attribute)

    def is_safe_callable(self, obj):
        # Only allow explicitly whitelisted callables or very basic types
        if obj in [range, dict, list, str, int, float, bool]:
            return True
        # Also allow Jinja2's safe_range which wraps range
        if getattr(obj, '__name__', '') == 'safe_range':
            return True
        return False


class PromptManager:
    _instance: Optional["PromptManager"] = None
    _is_initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, prompt_dir: str = "config/prompts"):
        if self._is_initialized:
            return

        self.prompt_dir = prompt_dir
        # Store both PromptTemplate model and compiled Jinja2 Template
        self.templates: Dict[Tuple[str, str], Tuple[PromptTemplate, Template]] = {}  # Key: (name, version)
        
        # Initialize SecureSandbox without a FileSystemLoader, as we compile from strings
        self.jinja_env = SecureSandbox(
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False, # We don't want autoescaping for LLM prompts, assume content is clean
            undefined=StrictUndefined, # Use StrictUndefined to raise errors for undefined variables
        )
        self._load_prompts()
        self._is_initialized = True
        logger.info(f"PromptManager initialized. Loaded {len(self.templates)} prompt templates.")

    def _load_prompts(self):
        """Loads all YAML prompt templates from the configured directory."""
        self.templates.clear()
        if not os.path.exists(self.prompt_dir):
            raise ConfigurationError(f"Prompt directory not found: {self.prompt_dir}")

        for root, _, files in os.walk(self.prompt_dir):
            for file in files:
                if file.endswith((".yaml", ".yml")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            prompt_data = yaml.safe_load(f)
                            
                            if not isinstance(prompt_data, dict):
                                logger.warning(f"Skipping malformed prompt file {file_path}: not a dictionary.")
                                continue
                            
                            # --- Determine name and version ---
                            explicit_name = prompt_data.get("name")
                            explicit_version = prompt_data.get("version")

                            # Try to infer from filename if not explicit
                            inferred_name = None
                            inferred_version = None
                            
                            relative_path_base = os.path.relpath(file_path, self.prompt_dir)
                            filename_without_ext = os.path.splitext(relative_path_base)[0]
                            
                            # Pattern for name_vX.Y.Z.yaml
                            match = re.match(r"^(.*)_v(\d+\.\d+\.\d+)$", filename_without_ext)
                            if match:
                                inferred_name = match.group(1).replace(os.sep, "/")
                                inferred_version = match.group(2)
                            else:
                                # Fallback to using full path as name if no explicit name or versioned filename
                                inferred_name = filename_without_ext.replace(os.sep, "/")

                            name = explicit_name or inferred_name
                            version = explicit_version or inferred_version or "1.0.0" # Default if nothing found

                            # Update prompt_data with determined name/version
                            prompt_data["name"] = name
                            prompt_data["version"] = version
                            
                            prompt_template = PromptTemplate(**prompt_data)
                            
                            # Compile Jinja2 template from the template string
                            compiled_template = self.jinja_env.from_string(prompt_template.template)

                            key = (prompt_template.name, prompt_template.version)
                            if key in self.templates:
                                logger.warning(f"Duplicate prompt template found: {name} v{prompt_template.version}. Overwriting with {file_path}.")
                            self.templates[key] = (prompt_template, compiled_template) # Store both
                            logger.debug(f"Loaded prompt template: {name} v{prompt_template.version} from {file_path}")
                    except yaml.YAMLError as e:
                        logger.error(f"Error parsing YAML file {file_path}: {e}")
                    except ValidationError as e:
                        logger.error(f"Validation error for prompt in {file_path}: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error loading prompt from {file_path}: {e}")

    @lru_cache(maxsize=128)
    def get_template(self, name: str, version: str = "1.0.0") -> PromptTemplate:
        """Retrieves a prompt template by name and version."""
        key = (name, version)
        template_pair = self.templates.get(key)
        if not template_pair:
            # Attempt to reload prompts if not found, in case new prompts were added
            self._load_prompts()
            template_pair = self.templates.get(key)
            if not template_pair:
                raise ResourceNotFoundError(f"Prompt template '{name}' version '{version}' not found.",
                                            resource_type="PromptTemplate", resource_id=f"{name}@{version}")
        return template_pair[0] # Return only the PromptTemplate model

    def render_template(self, prompt_name: str, prompt_version: str = "1.0.0", **kwargs) -> str:
        """
        Renders a prompt template with the given variables.
        Performs validation of input variables.
        """
        # Retrieve the PromptTemplate model and compiled Jinja2 Template
        template_pair = self.templates.get((prompt_name, prompt_version))
        if not template_pair:
            # This case should ideally not be reached if get_template is called first
            # but as a safeguard, try to get and compile the template
            prompt_template_model = self.get_template(prompt_name, prompt_version)
            compiled_template = self.jinja_env.from_string(prompt_template_model.template)
            self.templates[(prompt_name, prompt_version)] = (prompt_template_model, compiled_template)
            template_pair = (prompt_template_model, compiled_template)
        
        prompt_template_model, compiled_template = template_pair

        # Validate input variables against the PromptTemplate model
        # Create a mutable copy of kwargs to apply defaults
        processed_kwargs = dict(kwargs)
        missing_vars = []
        for var_name, var_info in prompt_template_model.input_variables.items():
            if var_name not in processed_kwargs:
                if var_info.get("required", True):
                    missing_vars.append(var_name)
                elif "default" in var_info:
                    processed_kwargs[var_name] = var_info["default"] # Apply default if missing and not required
        
        logger.debug(f"Prompt '{prompt_name}' v{prompt_version}: processed_kwargs={processed_kwargs}, missing_vars={missing_vars}")

        if missing_vars:
            raise ValidationError(
                f"Missing required input variables for prompt '{prompt_name}' v{prompt_version}: {', '.join(missing_vars)}",
                details={"prompt_name": prompt_name, "version": prompt_version, "missing_variables": missing_vars}
            )

        # Filter kwargs to only include expected input_variables
        # This prevents unexpected variables from being passed to the template rendering,
        # which could expose sensitive data or cause unexpected behavior.
        filtered_kwargs = {
            k: v for k, v in processed_kwargs.items()
            if k in prompt_template_model.input_variables
        }

        try:
            rendered_prompt = compiled_template.render(**filtered_kwargs)
            return rendered_prompt
        except TemplateError as e:
            logger.debug(f"Caught TemplateError in render_template for '{prompt_name}': {e}")
            raise MAIException(
                f"Error rendering prompt '{prompt_name}' v{prompt_version}: {e}",
                error_code="PROMPT_RENDER_ERROR",
                details={"prompt_name": prompt_name, "version": prompt_version, "template_error": str(e)}
            )
        except Exception as e:
            raise MAIException(
                f"An unexpected error occurred during prompt rendering for '{prompt_name}' v{prompt_version}: {e}",
                error_code="UNEXPECTED_PROMPT_RENDER_ERROR",
                details={"prompt_name": prompt_name, "version": prompt_version, "error": str(e)}
            )

    def reload_prompts(self):
        """Clears cache and reloads all prompt templates."""
        self.templates.clear()
        # Clear caches for lru_cache decorated methods
        self.get_template.cache_clear()
        # render_template no longer has lru_cache
        self._is_initialized = False # Force re-initialization to reload
        self.__init__(self.prompt_dir)
        logger.info("PromptManager reloaded all prompt templates.")

# Initialize the manager as a singleton on import
prompt_manager = PromptManager()
