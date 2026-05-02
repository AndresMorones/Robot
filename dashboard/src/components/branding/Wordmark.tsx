// Top-of-dashboard ACME LOGISTICS wordmark — concept B2 (mid-dot two-tone),
// locked variant: both words in the same ink color, only the interpunct
// carries the DOT-orange accent. Sits centered between page title (left)
// and date picker (right) in the sticky header.

export function Wordmark(): React.JSX.Element {
  return (
    <div
      aria-label="Acme Logistics"
      className="inline-flex select-none items-center gap-2.5 text-[13px] font-bold uppercase tracking-[0.22em] text-foreground"
    >
      <span>ACME</span>
      <span className="-translate-y-px text-[18px] leading-none text-[#F97316]">·</span>
      <span>LOGISTICS</span>
    </div>
  );
}
