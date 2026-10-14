# xadv-realuser-3 — two Indian companies with near-identical names

Lens: Indian Bank vs Indian Overseas Bank vs South Indian Bank; Kirloskar Oil Engines vs Kirloskar Industries (formerly Kirloskar Oil Engines)
vs Kirloskar Brothers vs Kirloskar Ferrous; ITC vs ITC Hotels; Siemens vs Siemens Energy India; Raymond vs Raymond Lifestyle. None in
r15/battery/manifest.json. Own stack :52910, region IN. Raw: `xadv-realuser-raw/` s3-names.txt, s4-resolve-renames.txt, s-autocomplete.txt.

## Outside truth

https://www.screener.in/company/KIRLOSIND/consolidated/ — "Kirloskar Industries Ltd", "BSE: 500243 | NSE: KIRLOSIND", "the listed core investment
company of the Kirloskar Group ... maintains strategic stakes in Kirloskar Brothers, Kirloskar Oil Engines, and Kirloskar Pneumatic" — a different
company from Kirloskar Oil Engines (KIRLOSENG), though KIRLOSIND's former legal name was Kirloskar Oil Engines Ltd (the product's former_names.json
row `KIRLOSIND: ["Kirloskar Oil Engines Limited"]`).
https://www.screener.in/company/ITCHOTELS/consolidated/ — "ITC Hotels Ltd", "BSE: 544325 | NSE: ITCHOTELS", "listed on the stock exchanges on 29 Jan'25".

## Results (GET /resolve; autocomplete where noted)

| typed | bound | runner-up |
|---|---|---|
| `Indian Bank` | INDIANB 1.0 | South Indian Bank 0.80, IOB 0.71 |
| `indian overseas bank` | IOB 1.0 | INDIANB 0.71 |
| `Indian Overseas` | IOB 0.92 | Vinny Overseas 0.65 |
| autocomplete `indian bank` | INDIANB, SOUTHBANK | |
| `Kirloskar Oil Engines` / `... Ltd` / `kirloskar oil` | KIRLOSENG 1.0 / 1.0 / 0.92 | KIRLOSIND 0.99 / 0.99 / 0.91, shown with former "Kirloskar Oil Engines Limited" |
| `ITC` | ITC Ltd (NSE) 1.0 | ITC BSE |
| `ITC Hotel` | ITCHOTELS 0.92 | ITC 0.60 |
| `Siemens` | SIEMENS 1.0 | |
| `Siemens Energy` | ENRIN 0.92 | SMERY/SMEGF (Siemens Energy AG ADR, US) 0.92 |
| `Raymond` | RAYMOND 1.0 | |
| `Raymond Lifestyle` | RAYMONDLSL 1.0 | RAYMOND 0.69 |

Every query binds the company a user means; the Kirloskar former-name trap correctly prefers the current Kirloskar Oil Engines and shows Kirloskar
Industries as the annotated runner-up. `Siemens Energy` binds the Indian listing in an IN session with the German ADRs as equal-score candidates —
locale tie-break, acceptable.

VERDICT xadv-realuser-3: pass
