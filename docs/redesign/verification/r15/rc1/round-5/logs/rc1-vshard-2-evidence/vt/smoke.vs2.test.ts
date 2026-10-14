import { historyForSend } from "@/store/chat-history";
test("smoke", () => { expect(typeof historyForSend).toBe("function"); });
