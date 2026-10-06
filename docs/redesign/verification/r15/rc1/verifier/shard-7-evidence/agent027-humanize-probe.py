import httpx, openai
from services.errors import humanize
class E(Exception):
    def __init__(s,code,msg): super().__init__(msg); s.status_code=code
req=httpx.Request("POST","https://x"); 
def oe(cls,code,body): return cls(message=body,response=httpx.Response(code,request=req),body=None)
cases=[
 ("openai",E(429,"Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details.', 'code': 'insufficient_quota'}}")),
 ("openai",E(429,"credit balance exhausted")),
 ("openai",E(400,"maximum context length is 128000 tokens")),
 ("groq",E(413,"Request too large")),
 ("ollama",httpx.ConnectError("All connection attempts failed")),
 ("ollama",httpx.ReadTimeout("timed out")),
 ("gemini",E(400,"{'error': {'code': 400, 'message': 'API key not valid. Please pass a valid API key.', 'status': 'INVALID_ARGUMENT', 'details': [{'reason': 'API_KEY_INVALID'}]}}")),
 ("xai",oe(openai.BadRequestError,400,"Incorrect API key provided: xa***. You can obtain an API key from https://console.x.ai.")),
 ("openrouter",E(400,"Error code: 400 - {'error': {'message': 'zzz-nonsense/not-a-model-9000:free is not a valid model ID'}}")),
 ("openrouter",E(429,"{'error':{'message':'Provider returned error','metadata':{'raw':'google/gemma-4-31b-it:free is temporarily rate-limited upstream','limit_source':'upstream_provider_shared_pool'},'user_id':'user_abc123'}}")),
 ("gemini",E(400,"The input token count (1200000) exceeds the maximum number of tokens allowed (1048576).")),
 ("groq",oe(openai.BadRequestError,400,"Error code: 400 - {'error': {'message': 'The model `mixtral-8x7b-32768` has been decommissioned', 'code': 'model_decommissioned'}}")),
 ("xai",oe(openai.PermissionDeniedError,403,"Error code: 403 - {'error': \"Your newly created team doesn't have any credits yet.\"}")),
 # fresh
 ("anthropic",E(400,"Your credit balance is too low to access the Anthropic API.")),
 ("mistral",E(401,"Unauthorized")),
 ("deepseek",E(402,"Insufficient Balance")),
 ("openai",E(404,"The model `gpt-9` does not exist or you do not have access to it.")),
 ("groq",E(429,"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_x` service tier `on_demand` on tokens per minute (TPM): Limit 12000, Used 11482, Requested 1639. Please try again in 5.605s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing")),
 ("gemini",E(429,"429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 15. Please retry in 31s.', 'status': 'RESOURCE_EXHAUSTED'}}")),
 ("anthropic",E(400,"prompt is too long: 215000 tokens > 200000 maximum")),
 ("mistral",E(400,"Prompt contains 140000 tokens and 0 draft tokens, too large for model with 131072 maximum context length")),
 ("deepseek",E(400,"This model's maximum context length is 65536 tokens. However, you requested 70000 tokens")),
 ("ollama",httpx.ConnectTimeout("timed out")),
 ("openrouter",E(400,"{'error':{'message':'This endpoint\\'s maximum context length is 32768 tokens. However, you requested about 40000 tokens','code':400}}")),
]
for p,e in cases:
    h=humanize(p,e); print(p.ljust(10), getattr(e,'status_code',type(e).__name__), '|', h.code, '|', h.message, '|', h.action, '| user_id' if 'user_abc123' in (h.detail or '') else '')
