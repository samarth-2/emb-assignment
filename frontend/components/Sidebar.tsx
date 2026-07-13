"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { deleteConversation } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import type { Conversation } from "@/lib/types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDeleted: () => void;
}

export default function Sidebar({ conversations, activeId, onSelect, onNewChat, onDeleted }: Props) {
  const router = useRouter();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string, event: React.MouseEvent) {
    event.stopPropagation();
    setDeletingId(id);
    try {
      await deleteConversation(id);
      if (id === activeId) onNewChat();
      onDeleted();
    } finally {
      setDeletingId(null);
    }
  }

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-white/10 bg-neutral-900">
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full rounded-lg bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/20"
        >
          + New Chat
        </button>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-2">
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            onClick={() => onSelect(conversation.id)}
            className={`group flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm ${
              conversation.id === activeId
                ? "bg-white/10 text-white"
                : "text-neutral-400 hover:bg-white/5 hover:text-neutral-200"
            }`}
          >
            <span className="truncate">{conversation.title}</span>
            <button
              onClick={(event) => handleDelete(conversation.id, event)}
              disabled={deletingId === conversation.id}
              className="ml-2 hidden shrink-0 text-neutral-500 hover:text-red-400 group-hover:block"
              aria-label="Delete conversation"
            >
              ✕
            </button>
          </div>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        <button
          onClick={handleLogout}
          className="w-full text-left text-sm text-neutral-400 hover:text-neutral-200"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
