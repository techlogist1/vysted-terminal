# free-maintainer-1 — news titles carry raw HTML entities into the UI (final-adv-maintainer, d38b5d1a)

- GET /news?limit=60 on the bundle binary (:52820, region IN): 2 of 60 items carry HTML entities in the title, both from "Markets-Economic Times": "F&amp;O Talk: 22,600 is a key Nifty support; …", "Bonus issues &amp; stock split: 5 stocks rewarding shareholders next week" (also seen on :52825).
- The News Feed renders `{item.title}` as text (src/modules/news/NewsFeedPanel.tsx:127), so the stranger first-run harness shows "F&amp;O Talk: …" literally (UI-7/harness-firstrun.json). No unescape step in sidecar/services/news_provider.py; the same strings reach the agent's news tool and research evidence.
- Duplicate check: no register entry mentions HTML entities/unescape in news.

VERDICT free-maintainer-1: finding maintainer:4
