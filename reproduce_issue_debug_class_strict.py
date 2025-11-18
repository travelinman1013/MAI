from jinja2 import StrictUndefined
from src.core.prompts.registry import SecureSandbox

class DebugSandbox(SecureSandbox):
    def is_safe_attribute(self, obj, attr, insecure_call=None):
        print(f"Checking safety: obj={type(obj)}, attr={attr}")
        result = super().is_safe_attribute(obj, attr, insecure_call)
        print(f"  Result: {result}")
        return result

env = DebugSandbox(undefined=StrictUndefined)
template_str = "{{ config.__class__ }}"
template = env.from_string(template_str)

config = {"SECRET_KEY": "unsafe_value"}

print("--- Rendering ---")
try:
    print(f"Rendered: {template.render(config=config)}")
except Exception as e:
    print(f"Caught error: {type(e).__name__}: {e}")
