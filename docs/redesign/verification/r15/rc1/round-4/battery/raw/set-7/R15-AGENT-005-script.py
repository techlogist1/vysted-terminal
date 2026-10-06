import sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand/sidecar")
from services.llm.native_search import native_search_available

cases = [
    ("groq", None, "llama-3.3-70b-versatile", False),
    ("gemini", None, "gemini-2.5-pro", False),
    ("groq", None, "groq/compound", True),
    ("gemini", None, "gemini-3-pro", True),
]
for provider, mws, model, expected in cases:
    got = native_search_available(provider, mws, model)
    status = "OK" if got == expected else "MISMATCH"
    print(f"{provider} {model}: native_search_available={got} expected={expected} [{status}]")
    assert got == expected, f"FAIL: {provider}/{model} expected {expected} got {got}"

# one-shot (no function tools) gemini-2.5-pro keeps google_search
got_oneshot = native_search_available("gemini", None, "gemini-2.5-pro", with_function_tools=False)
print(f"gemini gemini-2.5-pro one-shot (no function tools): native_search_available={got_oneshot} expected=True")
assert got_oneshot is True

print("PASS AGENT-005: groq/gemini native-search gating is per-model as certified")
