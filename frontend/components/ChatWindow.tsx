"use client";

import { useEffect, useRef, useState } from "react";
import { streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import MessageBubble from "@/components/MessageBubble";

interface Props {
  conversationId: string | null;
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  onConversationCreated: (id: string) => void;
}

export default function ChatWindow({
  conversationId,
  messages,
  setMessages,
  onConversationCreated,
}: Props) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setSending(true);

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      tool_used: null,
      generated_sql: null,
      citations: null,
      created_at: new Date().toISOString(),
    };
    const assistantId = crypto.randomUUID();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      tool_used: null,
      generated_sql: null,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    const patch = (updater: (message: ChatMessage) => ChatMessage) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? updater(m) : m)));

    try {
      await streamChat(
        { conversation_id: conversationId, message: text },
        {
          onMeta: (meta) => {
            if (!conversationId) onConversationCreated(meta.conversation_id);
            patch((m) => ({
              ...m,
              tool_used: meta.tool_used,
              generated_sql: meta.generated_sql,
              citations: meta.citations,
            }));
          },
          onToken: (delta) => patch((m) => ({ ...m, content: m.content + delta })),
          onError: (detail) => patch((m) => ({ ...m, content: detail || "Something went wrong." })),
        },
      );
    } catch {
      patch((m) => ({ ...m, content: "Something went wrong. Please try again." }));
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-sm text-neutral-500">
            Ask about Northwind Gadgets policies or orders.
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-white/10 p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Message the assistant..."
            className="flex-1 resize-none rounded-xl bg-neutral-800 px-4 py-3 text-sm text-white placeholder-neutral-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => void handleSend()}
            disabled={sending || !input.trim()}
            className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
