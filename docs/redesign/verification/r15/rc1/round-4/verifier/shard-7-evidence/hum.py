import httpx, openai
from services.errors import humanize
req = httpx.Request("POST", "https://x/v1/chat/completions")
def oe(cls, status, body):
    r = httpx.Response(status, request=req, json=body)
    return cls(message=f"Error code: {status} - {body}", response=r, body=body)
try:
    from google.genai.errors import ClientError
    def ge(status, body): return ClientError(status, body)
except Exception as e:
    ge = None; print("no genai", e)
cases = [
 ("openai", oe(openai.RateLimitError, 429, {"error":{"message":"You exceeded your current quota, please check your plan and billing details.","type":"insufficient_quota","code":"insufficient_quota"}})),
 ("openai", oe(openai.RateLimitError, 429, {"error":{"message":"credit balance exhausted","code":"credit_balance_exhausted"}})),
 ("openai", oe(openai.BadRequestError, 400, {"error":{"message":"This model's maximum context length is 128000 tokens. However, your messages resulted in 130000 tokens.","code":"context_length_exceeded"}})),
 ("groq", oe(openai.APIStatusError, 413, {"error":{"message":"Request too large"}})),
 ("groq", oe(openai.BadRequestError, 400, {"error":{"message":"The model `mixtral-8x7b-32768` has been decommissioned and is no longer supported.","code":"model_decommissioned"}})),
 ("xai", oe(openai.PermissionDeniedError, 403, {"code":"The caller does not have permission","error":"Your newly created teams doesn't have any credits yet. You can purchase credits on https://console.x.ai"})),
 ("xai", oe(openai.BadRequestError, 400, {"code":"Client specified an invalid argument","error":"Incorrect API key provided: xa***. You can obtain an API key from https://console.x.ai."})),
 ("openrouter", oe(openai.BadRequestError, 400, {"error":{"message":"zzz-nonsense/not-a-model-9000:free is not a valid model ID","code":400}})),
 ("openrouter", oe(openai.RateLimitError, 429, {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream","provider_name":"Google AI Studio"}},"user_id":"user_abc"})),
 ("ollama", httpx.ConnectError("All connection attempts failed")),
 ("ollama", httpx.ReadTimeout("timed out")),
 # fresh
 ("anthropic", oe(openai.BadRequestError, 400, {"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits."}})),
 ("anthropic", oe(openai.BadRequestError, 400, {"type":"error","error":{"type":"invalid_request_error","message":"prompt is too long: 215000 tokens > 200000 maximum"}})),
 ("mistral", oe(openai.BadRequestError, 400, {"object":"error","message":"Prompt contains 140000 tokens and 0 draft tokens, too large for model with 131072 maximum context length","type":"invalid_request_message_error"})),
 ("deepseek", oe(openai.APIStatusError, 402, {"error":{"message":"Insufficient Balance","type":"unknown_error"}})),
 ("openai", oe(openai.NotFoundError, 404, {"error":{"message":"The model `gpt-9` does not exist or you do not have access to it.","code":"model_not_found"}})),
 ("ollama", httpx.ConnectError("[Errno 61] Connection refused")),
 ("ollama", oe(openai.NotFoundError, 404, {"error":"model \"llama9:70b\" not found, try pulling it first"})),
 ("groq", oe(openai.BadRequestError, 400, {"error":{"message":"The model `llama-9-foo` does not exist or you do not have access to it.","type":"invalid_request_error","code":"model_not_found"}})),
 ("openrouter", oe(openai.BadRequestError, 400, {"error":{"message":"This endpoint's maximum context length is 32768 tokens. However, you requested about 40000 tokens","code":400}})),
]
if ge:
    cases += [("gemini", ge(400, {"error":{"code":400,"message":"API key not valid. Please pass a valid API key.","status":"INVALID_ARGUMENT","details":[{"reason":"API_KEY_INVALID"}]}})),
              ("gemini", ge(400, {"error":{"code":400,"message":"The input token count (1200000) exceeds the maximum number of tokens allowed (1048576).","status":"INVALID_ARGUMENT"}})),
              ("gemini", ge(404, {"error":{"code":404,"message":"models/gemini-9-pro is not found for API version v1beta","status":"NOT_FOUND"}})),
              ("gemini", ge(429, {"error":{"code":429,"message":"You exceeded your current quota, please check your plan and billing details.","status":"RESOURCE_EXHAUSTED"}}))]
for p, e in cases:
    h = humanize(p, e)
    print(f"{p:10} {type(e).__name__:22} {h.code:20} | {h.message} | {h.action} | uid_leak={'user_abc' in (h.detail or '')}")
