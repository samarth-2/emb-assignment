import type { Citation } from "@/lib/types";

export default function Citations({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-2 space-y-1 border-t border-white/10 pt-2">
      {citations.map((citation, index) => (
        <div key={index} className="text-xs text-neutral-400">
          <span className="font-medium text-neutral-300">{citation.document}</span>
          {citation.section && <span> — {citation.section}</span>}
        </div>
      ))}
    </div>
  );
}
