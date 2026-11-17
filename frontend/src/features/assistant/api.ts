import { api } from "../../shared/api/client";
import type { Page } from "../../shared/contracts";
import type { AiStatus, Answer, ChatMessage, Conversation } from "./types";

export function fetchAiStatus(signal: AbortSignal) {
  return api<AiStatus>("/ai/status", { signal });
}
export function fetchConversations(page: number, signal: AbortSignal) {
  return api<Page<Conversation>>(`/ai/conversations?page=${page}&page_size=10`, {
    signal,
  });
}
export function createConversation(title = "Cuộc trò chuyện mới") {
  return api<Conversation>("/ai/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}
export function fetchMessages(id: string, page: number, signal: AbortSignal) {
  return api<Page<ChatMessage>>(
    `/ai/conversations/${id}/messages?page=${page}&page_size=50`,
    { signal },
  );
}
export function sendMessage(
  id: string,
  message: string,
  requestId: string,
  signal: AbortSignal,
) {
  return api<Answer>(
    `/ai/conversations/${id}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ message, client_request_id: requestId }),
      signal,
    },
    45_000,
  );
}
