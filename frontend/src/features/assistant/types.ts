export type AiStatus = {
  available: boolean;
  mode: "disabled" | "openai" | "mock";
  message: string;
};
export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};
export type Source = { type: string; sku: string | null; as_of: string };
export type ChatMessage = {
  id: string;
  client_request_id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  sources: Source[];
  tool_calls: string[];
  created_at: string;
};
export type Answer = {
  message_id: string;
  answer: string;
  sources: Source[];
  tool_calls: string[];
};
