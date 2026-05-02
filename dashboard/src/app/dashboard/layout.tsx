import { Header } from "@/components/header";
import { LiveRefresh } from "@/components/live-refresh";
import { Sidebar } from "@/components/sidebar";

// Dashboard chrome shared by every /dashboard/* route:
//   - <Sidebar />       -> brand mark + primary nav (Overview / Calls / New
//                          Bookings), left vertical, sticky full-height.
//   - <Header />        -> sticky top bar holding only the DateRangePicker
//                          (right-aligned), stays visible on scroll.
//   - <LiveRefresh />   -> SSE subscription, calls router.refresh() on
//                          `call-ended` (paired with `revalidate=300` ISR
//                          fallback per ADR-009).
//
// Layout per locked user direction (2026-04-30): nav moved off the top bar
// onto a left sidebar; carriers route removed; theme toggle + active-call
// indicator + "Last 7 days" placeholder removed.
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <LiveRefresh />
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="container py-6">{children}</main>
      </div>
    </div>
  );
}
