import { writeFileSync } from "node:fs";
import { historyForSend, type ChatMessage } from "@/store/chat-history";
function thread(answerChars: number, exchanges: number): ChatMessage[] {
  const m: ChatMessage[] = [];
  m.push({ id: "u1", role: "user", content: "I only care about FY26 guidance vs delivery for BDL, ignore the chart" });
  m.push({ id: "a1", role: "assistant", content: "Noted. " + "x".repeat(answerChars), toolSteps: ["Using resolve symbol"] });
  for (let i = 2; i <= exchanges; i++) {
    m.push({ id: "u" + i, role: "user", content: `follow-up question ${i} about BDL order book` });
    m.push({ id: "a" + i, role: "assistant", content: `Answer ${i}. ` + "y".repeat(answerChars) });
  }
  return m;
}
test("dump", () => {
  const out: Record<string, unknown> = {};
  for (const [label, chars, n] of [["short-6x", 400, 6], ["research-6x-12k", 12000, 6], ["chat-20x-3.5k", 3500, 20]] as const) {
    const sent = historyForSend(thread(chars, n));
    out[label] = { total_in_thread: n * 2, sent: sent.length, first_sent: sent[0]?.content.slice(0, 60), turn1_sent: sent.some((s) => s.content.includes("FY26 guidance")), sent_history: sent };
  }
  writeFileSync(process.env.A040_OUT!, JSON.stringify(out));
});
