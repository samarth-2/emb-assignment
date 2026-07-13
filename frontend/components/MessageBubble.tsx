import type { ChatMessage } from "@/lib/types";
import Citations from "@/components/Citations";
import SqlBlock from "@/components/SqlBlock";
import ToolBadge from "@/components/ToolBadge";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl rounded-2xl px-4 py-3 ${
          isUser ? "bg-blue-600 text-white" : "bg-neutral-800 text-neutral-100"
        }`}
      >
        {!isUser && message.tool_used && message.tool_used !== "none" && (
          <ToolBadge toolUsed={message.tool_used} />
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content || (isUser ? "" : "…")}
        </p>
        {!isUser && message.generated_sql && <SqlBlock sql={message.generated_sql} />}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} />
        )}
      </div>
    </div>
  );
}
