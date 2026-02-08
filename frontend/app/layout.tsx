import type { Metadata } from "next";
import { IBM_Plex_Mono, Sora } from "next/font/google";

import "./globals.css";

const sora = Sora({ subsets: ["latin"], variable: "--font-display" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-mono", weight: ["400", "500", "700"] });

export const metadata: Metadata = {
  title: "Astra-Gemma",
  description: "Agentic in-silico clinical trial engine powered by MedGemma",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sora.variable} ${plexMono.variable}`}>{children}</body>
    </html>
  );
}
