cd /Users/lokavyasingh/Documents/dev/vysted-terminal
O=$1
for i in 1 2 3 4 5; do
  python3 scripts/r15/vy.py invoke copilot "How many ordinary shares does one SIFY ADR represent, and what is SIFY's TTM revenue in USD?" --port 52310 --provider ollama --model llama3.1:8b --autonomy ask --out $O/sify-$i.jsonl --timeout 600 > $O/sify-$i.txt 2>&1
  echo "run $i exit $?"
done
echo DONE
