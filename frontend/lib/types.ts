export type ToolUsed = "rag" | "sql" | "both" | "none";

export interface Citation {
  document: string;
  section: string | null;
  snippet: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_used: ToolUsed | null;
  generated_sql: string | null;
  citations: Citation[] | null;
  created_at: string;
}

export interface ChatMeta {
  conversation_id: string;
  message_id: string;
  tool_used: ToolUsed;
  generated_sql: string | null;
  citations: Citation[];
}
