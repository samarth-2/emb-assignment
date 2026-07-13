import { getToken } from "@/lib/auth";
import type { ChatMeta, ChatMessage, Conversation } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function authedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}

export async function login(username: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Invalid username or password");
  }
  const data = await res.json();
  return data.access_token as string;
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await authedFetch("/conversations");
  if (!res.ok) throw new Error("Failed to load conversations");
  return res.json();
}

export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  const res = await authedFetch(`/conversations/${conversationId}/messages`);
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await authedFetch(`/conversations/${conversationId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

interface StreamChatHandlers {
  onMeta?: (meta: ChatMeta) => void;
  onToken?: (delta: string) => void;
  onDone?: (data: { message_id: string }) => void;
  onError?: (detail: string) => void;
}

/**
 * Consumes the /chat SSE stream by hand (not EventSource, which can't send a
 * POST body or an Authorization header): read raw bytes, split on blank-line
 * event boundaries, parse each "event:"/"data:" pair.
 */
export async function streamChat(
  payload: { conversation_id: string | null; message: string },
  handlers: StreamChatHandlers,
): Promise<void> {
  const res = await authedFetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    handlers.onError?.(`Request failed (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let separatorIndex: number;
    while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      const eventMatch = rawEvent.match(/^event: (.+)$/m);
      const dataMatch = rawEvent.match(/^data: (.+)$/m);
      if (!eventMatch || !dataMatch) continue;

      const eventType = eventMatch[1].trim();
      const data = JSON.parse(dataMatch[1]);

      switch (eventType) {
        case "meta":
          handlers.onMeta?.(data as ChatMeta);
          break;
        case "token":
          handlers.onToken?.(data.delta as string);
          break;
        case "done":
          handlers.onDone?.(data);
          break;
        case "error":
          handlers.onError?.(data.detail as string);
          break;
      }
    }
  }
}
