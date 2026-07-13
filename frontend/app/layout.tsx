import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northwind Gadgets Assistant",
  description: "Dual-mode agentic RAG chatbot for Northwind Gadgets",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-neutral-950 text-neutral-100">{children}</body>
    </html>
  );
}
