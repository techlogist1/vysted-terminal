from services import bse_provider as b
r=b._http_get(b._SHP_INDEX_URL+"?scripcode=530017"); print('plain httpx', r.status_code, r.text[:120])
try:
    p=b._api_json("SHPQNewFormat/w", {"scripcode":"530017"}); print('_api_json', type(p).__name__, str(p)[:300])
except Exception as e: print('_api_json err', e)
