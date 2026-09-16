import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Regional Media Intelligence Agent",
  description: "AI-powered regional media intelligence platform. Transforms newspaper scans into actionable intelligence using local open-source AI models.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-surface-50">
          <div className="max-w-[1600px] mx-auto p-6 lg:p-8">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
