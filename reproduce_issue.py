from jinja2 import Template
from src.core.prompts.registry import SecureSandbox

env = SecureSandbox()
template_str = "{{ config.SECRET_KEY }}"
template = env.from_string(template_str)

config = {"SECRET_KEY": "unsafe_value"}

try:
    print(f"Rendered: {template.render(config=config)}")
except Exception as e:
    print(f"Caught expected error: {type(e).__name__}: {e}")

template_str_2 = "{{ config['SECRET_KEY'] }}"
template_2 = env.from_string(template_str_2)
try:
    print(f"Rendered item access: {template_2.render(config=config)}")
except Exception as e:
    print(f"Caught error item access: {type(e).__name__}: {e}")
