
from typing import Any, Callable, Optional, TypeVar, get_origin, get_args
from functools import wraps
import inspect # Import inspect for signature extraction
import asyncio
from inspect import iscoroutinefunction as _is_coroutine_function

from pydantic import BaseModel, Field, create_model, ValidationError, RootModel
from pydantic.fields import FieldInfo # For creating Pydantic models from signatures

from src.core.tools.registry import tool_registry # Import the global registry
from src.core.utils.exceptions import ToolExecutionError
from src.core.utils.logging import get_logger_with_context

# A generic type for the callable that represents a tool function.
ToolFunc = TypeVar("ToolFunc", bound=Callable[..., Any])
logger = get_logger_with_context(module="tool_base")

from src.core.tools.models import ToolMetadata
def tool(
    name: str,
    description: str,
    category: str = "general",
    version: str = "1.0.0",
    enabled: bool = True,
) -> Callable[[ToolFunc], ToolFunc]:
    """
    Decorator to register a function as an AI agent tool.

    This decorator extracts function signature to automatically generate
    JSON schema for tool parameters and return type. It also adds input
    and output validation using Pydantic and integrates logging.

    Args:
        name: The unique name of the tool.
        description: A brief, clear description of what the tool does.
        category: The category the tool belongs to.
        version: The version of the tool.
        enabled: Whether the tool is currently enabled.

    Returns:
        A decorator that registers the function as a tool.

    Example:+
        ```python
        from src.core.tools.base import tool

        @tool(name="get_current_time", description="Returns the current UTC time.")
        def get_current_time() -> str:
            import datetime
            return datetime.datetime.utcnow().isoformat()
        ```
    """

    def decorator(func: ToolFunc) -> ToolFunc:
        sig = inspect.signature(func)
        
        # --- Parameter (Input) Validation ---
        param_fields = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self" or param_name == "cls": # Skip self/cls in methods
                continue

            param_type = Any if param.annotation is inspect.Parameter.empty else param.annotation
            
            # Handle Optional types correctly for default values
            if get_origin(param_type) is Optional:
                actual_type = get_args(param_type)[0]
                # If Optional[X] and default is None, set default to None
                default_value = None if param.default is inspect.Parameter.empty else param.default
                param_fields[param_name] = (Optional[actual_type], default_value)
            else:
                default_value = ... if param.default is inspect.Parameter.empty else param.default
                param_fields[param_name] = (param_type, default_value)
        
        ParametersModel = create_model(f"{name.capitalize()}Parameters", **param_fields)
        parameters_schema = ParametersModel.model_json_schema()

        # --- Return (Output) Validation ---
        return_annotation = sig.return_annotation
        
        if return_annotation is inspect.Signature.empty:
            root_type = Any
        elif get_origin(return_annotation) is Optional:
             root_type = get_args(return_annotation)[0] | None
        else:
            root_type = return_annotation
        
        # Define a temporary RootModel for the return type
        class TempReturnRootModel(RootModel[root_type]): # type: ignore
            pass
        returns_schema = TempReturnRootModel.model_json_schema()
        
        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters_schema,
            returns=returns_schema, # Add return schema to metadata
            version=version,
            enabled=enabled,
        )

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger.info(f"Executing tool '{name}'", tool_name=name, args=args, kwargs=kwargs)
            try:
                # Input validation
                validated_params = ParametersModel.model_validate(
                    {**dict(zip(sig.parameters.keys(), args)), **kwargs}
                )
                
                # Execute the tool function with validated arguments
                func_args_kwargs = validated_params.model_dump(exclude_unset=True)

                # Call the original (possibly further decorated) function
                result = await func(**func_args_kwargs) if _is_coroutine_function(func) else func(**func_args_kwargs)
                
                # Output validation
                validated_result = TempReturnRootModel.model_validate(result)
                logger.info(f"Tool '{name}' executed successfully.", tool_name=name)
                return validated_result.root
            except ValidationError as e:
                logger.error("Validation error for tool '{tool_name}': {error}", tool_name=name, error=str(e))
                raise ToolExecutionError(f"Validation error for tool '{name}': {e}") from e
            except Exception as e:
                logger.error("Error executing tool '{tool_name}': {error}", tool_name=name, error=str(e))
                raise ToolExecutionError(f"Error executing tool '{name}': {e}") from e

        # Determine if the original function is async
        if _is_coroutine_function(func):
            wrapper = async_wrapper
        else:
            # If the tool is sync, we can just call it directly after validation
            # and before output validation. No need for a separate sync_wrapper.
            @wraps(func)
            def sync_wrapper_with_validation(*args, **kwargs) -> Any:
                logger.info(f"Executing tool '{name}' (sync)", tool_name=name, args=args, kwargs=kwargs)
                try:
                    # Input validation
                    validated_params = ParametersModel.model_validate(
                        {**dict(zip(sig.parameters.keys(), args)), **kwargs}
                    )
                    
                    func_args_kwargs = validated_params.model_dump(exclude_unset=True)
                    
                    # Call the original (possibly further decorated) function
                    result = func(**func_args_kwargs) # Direct sync call
                    
                    # Output validation
                    validated_result = TempReturnRootModel.model_validate(result)
                    logger.info(f"Tool '{name}' executed successfully (sync).", tool_name=name)
                    return validated_result.root
                except ValidationError as e:
                    logger.error("Validation error for tool '{tool_name}': {error}", tool_name=name, error=str(e))
                    raise ToolExecutionError(f"Validation error for tool '{name}': {e}") from e
                except Exception as e:
                    logger.error("Error executing tool '{tool_name}': {error}", tool_name=name, error=str(e))
                    raise ToolExecutionError(f"Error executing tool '{name}': {e}") from e
            wrapper = sync_wrapper_with_validation

        # Attach metadata to the wrapper
        wrapper.__tool_metadata__ = metadata # type: ignore

        # Register the tool using the global registry
        tool_registry.register(wrapper, metadata)

        return wrapper # type: ignore

    return decorator

