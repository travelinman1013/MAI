from jinja2 import StrictUndefined
from src.core.prompts.registry import SecureSandbox

class StrictDotSandbox(SecureSandbox):
    def getattr(self, obj, attribute):
        print(f"StrictDotSandbox.getattr called for {type(obj)} . {attribute}")
        if isinstance(obj, dict):
            # For dicts, enforce is_safe_attribute check.
            # Since is_safe_attribute returns False for non-whitelisted attributes (like 'SECRET_KEY'),
            # this should block it.
            if not self.is_safe_attribute(obj, attribute, obj):
                 return self.unsafe_undefined(obj, attribute)
            
            # If safe, try to get attribute. 
            # Note: We intentionally DO NOT fall back to item lookup here to block dict.key access.
            try:
                return getattr(obj, attribute)
            except AttributeError:
                # If attribute doesn't exist (and we don't fallback), return undefined.
                return self.undefined(obj=obj, name=attribute)

        return super().getattr(obj, attribute)

env = StrictDotSandbox(undefined=StrictUndefined)
template_str = "{{ config.SECRET_KEY }}"
template = env.from_string(template_str)

config = {"SECRET_KEY": "unsafe_value"}

print("--- Rendering ---")
try:
    print(f"Rendered: {template.render(config=config)}")
except Exception as e:
    print(f"Caught error: {type(e).__name__}: {e}")
