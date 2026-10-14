import sys, json; sys.path.insert(0, sys.argv[1])
from services import agent_runtime as ar
d=json.load(open(sys.argv[2]))
for k,v in d.items():
    msgs, folded = ar._coerce_history(v["sent_history"])
    summ = msgs[0].content if folded else ""
    print(k, "client_sent", v["sent"], "runtime_folded", folded, "verbatim", len(msgs)-(1 if folded else 0),
          "| turn-1 constraint in provider history:", any("FY26 guidance" in m.content for m in msgs),
          "| summary head:", summ.splitlines()[:2])
