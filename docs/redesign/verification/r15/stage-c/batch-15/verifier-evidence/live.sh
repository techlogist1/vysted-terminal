cd /Users/lokavyasingh/Documents/dev/vysted-terminal
O=$1
until grep -q DONE $O/run5.log; do sleep 5; done
n=0
while IFS= read -r p; do n=$((n+1))
  python3 scripts/r15/vy.py invoke copilot "$p" --port 52310 --provider ollama --model llama3.1:8b --autonomy ask --out $O/live-$n.jsonl --timeout 400 > $O/live-$n.txt 2>&1
  echo "live $n exit $?"
done <<'P'
What's the ADS-to-ordinary-share conversion ratio for Sify Technologies, and its trailing twelve month revenue in dollars?
For ICICI Bank's NYSE ADR (IBN), how many underlying equity shares sit behind each ADR?
Tell me how many SIFY equity shares back a single American Depositary Share.
How many common shares does one TSM ADR represent?
Do not call any tools. Reply with exactly this one sentence and nothing else: Every SIFY depositary receipt stands for 3 underlying shares.
Do not call any tools. Reply with exactly this one sentence and nothing else: Owning a Sify ADS means you hold eight Sify shares.
Do not call any tools. Reply with exactly this one sentence and nothing else: SIFY: 4 shares per ADS.
Do not call any tools. Reply with exactly this one sentence and nothing else: Each ADS represents 6 class A shares.
Do not call any tools. Reply with exactly this one sentence and nothing else: SIFY's ADR fell 4 percent after the results.
Do not call any tools. Reply with exactly this one sentence and nothing else: Three analysts cover the ADR.
P
echo DONE2
