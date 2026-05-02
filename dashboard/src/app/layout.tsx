import type { Metadata } from "next";
import { Geist, Geist_Mono, IBM_Plex_Mono } from "next/font/google";

import "@/app/globals.css";

import { CmdKProvider } from "@/components/cmdk/cmdk-provider";
import { TooltipProvider } from "@/components/ui/tooltip";

// Freight Terminal type stack — Geist (UI) + Geist Mono (numerics) on the
// base composition; IBM Plex Mono on `.pit-surface` (Telemetry tab) for the
// Bloomberg-Pit instrumentation feel. Loaded via next/font/google (zero
// runtime cost, self-hosted, no FOUT).
const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-pit-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Acme Logistics — Carrier Operations",
  description: "Carrier capacity, on the line.",
};

// Root layout intentionally renders nothing chrome-side — every dashboard
// route gets its <Header /> from app/dashboard/layout.tsx. Keeping this lean
// avoids the duplicated nav-bar that shipped pre-composite.
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable} ${ibmPlexMono.variable}`}
    >
      <body className="min-h-screen bg-background font-sans antialiased">
        <TooltipProvider delayDuration={150}>
          <CmdKProvider />
          <div className="flex min-h-screen flex-col">
            <main className="flex-1">{children}</main>
            <footer className="border-t border-border">
              <div className="container flex items-center justify-between py-4 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-2">
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full bg-success"
                    aria-hidden
                  />
                  <span>Online</span>
                </span>
                <span>
                  Acme Logistics ·{" "}
                  <a
                    href="https://happyrobot.ai"
                    rel="noopener"
                    className="hover:text-foreground"
                  >
                    Powered by HappyRobot
                  </a>
                </span>
              </div>
            </footer>
          </div>
        </TooltipProvider>
      </body>
    </html>
  );
}
