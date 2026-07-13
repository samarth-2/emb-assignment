"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ChatWindow from "@/components/ChatWindow";
import Sidebar from "@/components/Sidebar";
import { getMessages, listConversations } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ChatMessage, Conversation } from "@/lib/types";

export default function ChatPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch {
      router.replace("/login");
    }
  }, [router]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setAuthChecked(true);
  }, [router]);

  useEffect(() => {
    if (authChecked) void refreshConversations();
  }, [authChecked, refreshConversations]);

  const selectConversation = useCallback(async (id: string) => {
    setActiveConversationId(id);
    setMessages(await getMessages(id));
  }, []);

  const startNewChat = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
  }, []);

  const handleConversationCreated = useCallback(
    (id: string) => {
      setActiveConversationId(id);
      void refreshConversations();
    },
    [refreshConversations],
  );

  if (!authChecked) return null;

  return (
    <div className="flex h-screen bg-neutral-950 text-neutral-100">
      <Sidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={(id) => void selectConversation(id)}
        onNewChat={startNewChat}
        onDeleted={() => void refreshConversations()}
      />
      <ChatWindow
        conversationId={activeConversationId}
        messages={messages}
        setMessages={setMessages}
        onConversationCreated={handleConversationCreated}
      />
    </div>
  );
}
