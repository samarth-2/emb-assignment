export default function SqlBlock({ sql }: { sql: string }) {
  return (
    <pre className="mt-2 overflow-x-auto rounded-lg bg-black/40 p-3 text-xs text-emerald-300">
      <code>{sql}</code>
    </pre>
  );
}
