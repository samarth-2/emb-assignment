import type { ToolUsed } from "@/lib/types";

const LABELS: Record<ToolUsed, string> = {
  rag: "Documents",
  sql: "Order data",
  both: "Documents + Order data",
  none: "Direct answer",
};

const COLORS: Record<ToolUsed, string> = {
  rag: "bg-emerald-500/15 text-emerald-400",
  sql: "bg-sky-500/15 text-sky-400",
  both: "bg-violet-500/15 text-violet-400",
  none: "bg-neutral-500/15 text-neutral-400",
};

export default function ToolBadge({ toolUsed }: { toolUsed: ToolUsed }) {
  return (
    <span
      className={`mb-2 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${COLORS[toolUsed]}`}
    >
      {LABELS[toolUsed]}
    </span>
  );
}
