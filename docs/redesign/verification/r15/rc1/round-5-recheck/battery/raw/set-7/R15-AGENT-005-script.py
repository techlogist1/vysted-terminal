import sys
sys.path.insert(0, ".")
from services.llm.native_search import native_search_available

cases = [
    ("groq", None, "llama-3.3-70b-versatile"),
    ("groq", None, "groq/compound"),
    ("gemini", None, "gemini-2.5-pro"),
    ("gemini", None, "gemini-3-pro"),
    ("xai", None, "grok-4"),
]
for provider, tools, model in cases:
    r = native_search_available(provider, tools, model)
    print(f"native_search_available({provider!r}, None, {model!r}) -> {r}")
