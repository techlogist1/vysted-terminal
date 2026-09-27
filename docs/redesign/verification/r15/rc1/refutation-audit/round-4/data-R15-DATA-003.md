# R15-DATA-003 (rc1-verifier:3) — refutation audit round 4, group data

Verdict: **regression_confirmed** (never fixed on the disclosure lanes the fix_shape names). Severity: critical (kept).

Audited 06:57 IST on own sidecar :52400 (sidecar/.venv uvicorn app:app, VYSTED_DATA_DIR=scratch, MCP ports 0). Code tree == 01015033 (git diff --name-only 01015033 HEAD outside docs/ printed nothing at start; HEAD later moved to 35cf5580 by lead docs commits that touch only docs/ and CHANGELOG.md; git diff 01015033 HEAD -- sidecar src types plugins src-tauri scripts is empty).

## Entry
- repro: GET /disclosures/shareholding?symbol=AMAL and /disclosures/announcements?symbol=AMAL&limit=25 for the NASDAQ:AMAL slot return a flat 200 with Amal Ltd's BSE data and no not-applicable signal.
- fix_shape: gate every India-only lane (ownership_check.is_applicable, corporate_disclosures shareholding/announcements) on the bound instrument's exchange in {NSE,BSE}, never bare-ticker master membership; explicit not-applicable for a non-Indian instrument.
- certified batch-2 (806a90c) on the research snapshot only (snapshot_structured('AMAL', US) had no ownership_exchange). The 806a90c diff changed ownership_check.is_applicable to witness.is_india_listing; corporate_disclosures.py only changed the dual-listed split merge (R15-CODE-DATA-001). The shareholding/announcements gate was never touched.

## 1. Entry's own repro + verifier's refutation (same curls, X-Vysted-Region: US) — sh d003.sh
```
HEAD 608a2d4b 06:47 IST

### curl -H X-Vysted-Region: US http://127.0.0.1:52400/disclosures/shareholding?symbol=AMAL
{"symbol":"AMAL","count":104,"patterns":[{"symbol":"AMAL","quarter_end":"2026-06-30","quarter_basis":null,"promoter_percent":71.35,"fii_percent":0.0,"dii_percent":0.03,"institutions_percent":0.03,"public_percent":28.65,"public_basis":"incl. institutions","public_non_institutional_percent":28.62,"employee_trusts_percent":null,"submission_date":"2026-07-05","xbrl_url":"https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/506597_57202695344_SP.html","source":"BSE","split_source":null,"split_as_of":null,"split_basis":"derived","promoter_pledged_percent":0.0,"promoter_pledge_basis":"filed"},{"symbol":"AMAL","quarter_end":"2026-03-31","quarter_basis":null,"promoter_percent":71.35,"fii_percent":0.0,"dii_percent":0.02,"institutions_percent":0.02,"public_percent":28.65,"public_basis":"incl. institutions","public_non_institutional_percent":28.64,"employee_trusts_percent":null,"submission_date":"2026-04-09","xbrl_url":"https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/506597_94202614185_SP.html","source":"BSE","split_source":null,"split_as_of":null,"split_basis":"derived","promoter_pledged_percent":0.0,"promoter_pledge_basis":"filed"},{"symbol":"AMAL","quarter_end":"2025-12-31","quarter_basis":n

### curl -H X-Vysted-Region: US http://127.0.0.1:52400/disclosures/announcements?symbol=AMAL&limit=25
{"symbol":"AMAL","exchange":null,"count":21,"announcements":[{"symbol":"AMAL","exchange":"BSE","headline":"[closure-of-window notice]","category":"[insider/SAST category]","attachment_url":"https://www.bseindia.com/xml-data/corpfiling/AttachLive/e85ba6f5-286f-442e-8b64-198596f75ead.pdf","ts":"2026-09-25T14:52:14.917000+05:30"},{"symbol":"AMAL","exchange":"BSE","headline":"Board Meeting Intimation for Meeting Of The Board Of Directors And [closure-of-window notice]","category":"Board Meeting","attachment_url":"https://www.bseindia.com/xml-data/corpfiling/AttachLive/a367018d-c66e-47bf-b42a-d997b07a5a0e.pdf","ts":"2026-09-25T14:47:31.283000+05:30"},{"symbol":"AMAL","exchange":"BSE","headline":"Speech Of Chairman / Video Recording / Presentation","category":"AGM/EGM","attachment_url":"https://www.bseindia.com/xml-data/corpfiling/AttachHis/143b2177-5969-412c-9f50-eb7d2aea3554.pdf","ts":"2026-08-20T16:07:26.060000+05:30"},{"symbol":"AMAL","exchange":"BSE","headline":"Shareholder Meeting / Postal Ballot-Scrutinizer''s Report","category":"AGM/EGM","attachment_url":"https://www.bseindia.com/xml-data/corpfiling/AttachHis/f2eb83b8-561b-437b-be85-3b7ca2f9ee98.pdf","ts":"2026-08-14T14:36:23.693000

### curl -H X-Vysted-Region: US http://127.0.0.1:52400/resolve?q=AMAL
{"ok":true,"query":"AMAL","region":"US","resolved":{"symbol":"AMAL","name":"Amalgamated Financial Corp.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"AMAL","confidence":1.0,"isin":"US0226711010","bse_code":null,"industry":null,"former_name":null,"board":null,"exchange_group":null,"face_value":null},"needs_disambiguation":false,"candidates":[{"symbol":"AMAL","name":"Amalgamated Financial Corp.","exchange":"US","region":"US","asset_class":"equity","yahoo_symbol":"AMAL","confidence":1.0,"isin":"US0226711010","bse_code":null,"industry":null,"former_name":null,"board":null,"exchange_group":null,"face_value":null},{"symbol":"AMAL","name":"Amal Limited","exchange":"NSE","region":"IN","asset_class":"equity","yahoo_symbol":"AMAL.NS","confidence":1.0,"isin":"INE841D01013","bse_code":"506597","industry":null,"former_name":null,"board":"mainboard","exchange_group":"B","face_value":10.0},{"symbol":"AMAL","name":"Amal Ltd","exchange":"BSE","region":"IN","asset_class":"equity","yahoo_symbol":"AMAL.BO","confidence":1.0,"isin":"INE841D01013","bse_code":"506597","industry":null,"former_name":null,"board":"mainboard","exchange_group":"B","face_value":10.0}],"rename_lane":"avai
[HTTP 200 3.139310s]


### curl -H X-Vysted-Region: US http://127.0.0.1:52400/disclosures/shareholding?symbol=SMR
{"symbol":"SMR","count":1,"patterns":[{"symbol":"SMR","quarter_end":"2026-06-04","quarter_basis":null,"promoter_percent":65.74,"fii_percent":9.88,"dii_percent":0.84,"institutions_percent":10.72,"public_percent":34.26,"public_basis":"incl. institutions","public_non_institutional_percent":23.55,"employee_trusts_percent":null,"submission_date":"2026-06-08","xbrl_url":"https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/544774_86202616343_SP.html","source":"BSE","split_source":null,"split_as_of":null,"split_basis":"filed","promoter_pledged_percent":0.0,"promoter_pledge_basis":"filed"}],"coverage":"covered","note":null,"provider":null,"major_shareholders":[],"source_url":null}
[HTTP 200 0.352605s]

```

## 2. Agent-tool path under region US (in-process, config.set_request_region('US'))
```
import asyncio, json, config
from services.agent_tools import disclosure_tools as dt
from services import ownership_check, symbol_resolver
async def main():
    tok = config.set_request_region("US")
    print("region", config.get_region())
    r = await dt._shareholding_pattern({"symbol": "AMAL"})
    p = r.get("patterns") or [{}]
    print("shareholding_pattern(AMAL) ok=%s coverage=%s note=%s count=%s latest promoter=%s xbrl=%s" % (r.get("ok"), r.get("coverage"), r.get("note"), r.get("count"), p[0].get("promoter_percent"), p[0].get("xbrl_url")))
    a = await dt._corporate_announcements({"symbol": "AMAL", "limit": 5})
    print("corporate_announcements(AMAL) ok=%s coverage=%s count=%s first=%s" % (a.get("ok"), a.get("coverage"), a.get("count"), (a.get("announcements") or [{}])[0].get("headline")))
    print("ownership_check.is_applicable('AMAL')=", ownership_check.is_applicable("AMAL"), " ('AMAL.BO')=", ownership_check.is_applicable("AMAL.BO"))
    print("is_bse_symbol(AMAL)=", symbol_resolver.is_bse_symbol("AMAL"))
asyncio.run(main())
---- output
region US
shareholding_pattern(AMAL) ok=True coverage=covered note=None count=12 latest promoter=71.35 xbrl=https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/506597_57202695344_SP.html
corporate_announcements(AMAL) ok=True coverage=covered count=5 first=[closure-of-window notice]
ownership_check.is_applicable('AMAL')= False  ('AMAL.BO')= True
is_bse_symbol(AMAL)= True
```

## 3. Copilot on llama3.1:8b, US region, two fresh phrasings (ollama lock held; vy.py copy with port guard widened to 52400 and ledger in scratch)
### d003-agent-1
```
{"kind": "tool_use", "tool_call_id": "call_0ee597f21bbd47e899c0d5e6a7c26034", "name": "shareholding_pattern", "input": {"symbol": "AMAL"}}
{"kind": "tool_result", "tool_call_id": "call_0ee597f21bbd47e899c0d5e6a7c26034", "name": "shareholding_pattern", "ok": true, "error": null}
{"kind": "done", "usage": {"input_tokens": 5240, "output_tokens": 54, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
=== ASSISTANT TEXT ===
The controlling shareholders of AMAL are the promoters who hold 71.35% of the shares. The institutions hold a negligible percentage of 0.02%, and the public holds 28.65%. There is no information available on the percentage held by insiders.

=== ok · 58.4s · events {'heartbeat': 4, 'tool_use': 1, 'tool_result': 1, 'delta': 55, 'done': 1} · usage in=5240 out=54 · est $0.00000 · llama3.1:8b
```
### d003-agent-2
```
{"kind": "tool_use", "tool_call_id": "call_9e1ba631be97430c9f6b45ab4f095914", "name": "corporate_announcements", "input": {"symbol": "AMAL"}}
{"kind": "tool_use", "tool_call_id": "call_9f29f478089e4054a5f26f06c51512e4", "name": "shareholding_pattern", "input": {"symbol": "AMAL"}}
{"kind": "tool_use", "tool_call_id": "call_d7f09848097c4273bbde170a351f0e2b", "name": "sec_filings_list", "input": {"symbol": "AMAL"}}
{"kind": "tool_result", "tool_call_id": "call_9e1ba631be97430c9f6b45ab4f095914", "name": "corporate_announcements", "ok": true, "error": null}
{"kind": "tool_result", "tool_call_id": "call_9f29f478089e4054a5f26f06c51512e4", "name": "shareholding_pattern", "ok": true, "error": null}
{"kind": "tool_result", "tool_call_id": "call_d7f09848097c4273bbde170a351f0e2b", "name": "sec_filings_list", "ok": false, "error": "sec-edgar-mcp is not available \u2014 the subprocess did not bind a port this launch (relaunch to retry)"}
{"kind": "done", "usage": {"input_tokens": 7607, "output_tokens": 177, "cache_read_input_tokens": null, "cache_creation_input_tokens": null, "web_search_requests": null}, "finish_reason": "stop", "context_window": 16384, "spend_usd": 0.0}
=== ASSISTANT TEXT ===
The latest ownership breakdown for AMAL shows that the promoter holding percentage is 71.35%, while the FII, DII, institutions, and public holding percentages are 0.0%, 0.03%, 0.03%, and 28.65% respectively.

Regarding recent company filings for AMAL, there have been several announcements in the past few months, including a [closure-of-window notice], a board meeting intimation, and a speech of chairman/video recording/presentation. However, due to an error with the sec-edgar-mcp tool, we are unable to retrieve the most up-to-date information on company filings.

Please note that these figures may not reflect the current ownership breakdown or recent company filings for AMAL. For more accurate and up-to-date information, I recommend checking the official websites of the exchanges or regulatory bodies where AMAL is listed.

=== ok · 96.8s · events {'heartbeat': 7, 'tool_use': 3, 'tool_result': 3, 'delta': 178, 'done': 1} · usage in=7607 out=177 · est $0.00000 · llama3.1:8b
```

## Code at HEAD
- sidecar/services/corporate_disclosures.py:1093-1103 get_shareholding gates on symbol_resolver.is_nse_symbol(bare)/is_bse_symbol(bare) (bare-ticker master membership); :532-547 get_announcements the same; also :696 results, :878 corporate actions, :1035 deals.
- sidecar/routers/disclosures.py:88-98 caches shareholding under disclosures:shareholding:<SYMBOL> with no region in the key; corporate_disclosures.py:606 the announcements cache likewise.
- sidecar/services/agent_tools/disclosure_tools.py:56-117 hands the service result through as ok:true, coverage 'covered'.
- The research gate IS fixed: ownership_check.is_applicable('AMAL') False, ('AMAL.BO') True (output above).

## Reasoning
The entry's own REST repro reproduces byte-for-byte at HEAD (104 BSE patterns, promoter 71.35, xbrl 506597_…; 21 BSE announcements) while /resolve under the same region binds Amalgamated Financial Corp (US0226711010). The refuter's objection that the REST routes have no frontend caller is true (grep src/ plugins/ for /disclosures/ finds none), but the same service functions back the copilot tools shareholding_pattern/corporate_announcements, and the live llama3.1:8b runs in a US session called shareholding_pattern(symbol=AMAL) and corporate_announcements(symbol=AMAL), got ok:true and told the user 'The controlling shareholders of AMAL are the promoters who hold 71.35%' and listed Amal Ltd's BSE announcements as AMAL's filings. The service already has a not_applicable coverage (_not_applicable, :618), but it is decided by bare-ticker master membership, which the fix_shape explicitly forbids. The batch-2 certification only exercised the research snapshot, so this lane was never fixed. The verifier's refutation holds.

## Certification failures
Baseline 0: the register note has no 'certification failures so far' clause; R15-DATA-003 is in no stage-c not_certified list (batch-2 certified it); no earlier REFUTATION_AUDIT has a regression_confirmed or partial verdict for it. Plus this verdict = 1.
