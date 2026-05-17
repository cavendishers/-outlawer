import type { Metadata } from "next";
import { Archivo_Black, Space_Grotesk } from "next/font/google";

import "./globals.css";
import { Navigation } from "@/components/nav";

const display = Archivo_Black({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const body = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Outlawer",
  description: "An online AI-assisted knowledge base with brutalist story views.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className={`${display.variable} ${body.variable} bg-paper text-ink`}>
        <div className="min-h-screen bg-[linear-gradient(to_right,#00000010_1px,transparent_1px),linear-gradient(to_bottom,#00000010_1px,transparent_1px)] bg-[size:28px_28px] px-4 py-4 md:px-6">
        <div className="mx-auto max-w-7xl border-4 border-ink bg-paper p-4 shadow-brutal md:p-6">
            <header className="mb-4 flex flex-col gap-4 border-4 border-ink bg-neon px-5 py-4 md:mb-5 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-display text-sm uppercase tracking-[0.3em]">Outlawer</p>
                <p className="text-xs font-black uppercase tracking-[0.2em]">Online Knowledge Arsenal</p>
              </div>
              <Navigation />
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
