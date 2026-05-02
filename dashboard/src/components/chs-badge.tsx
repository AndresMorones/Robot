import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function ChsBadge({
  value,
  className,
}: {
  value: number | null | undefined;
  className?: string;
}) {
  if (value === null || value === undefined) {
    return (
      <Badge variant="outline" className={cn("font-normal", className)}>
        —
      </Badge>
    );
  }
  const v = Math.max(0, Math.min(100, Math.round(value)));
  // Pass threshold (locked at 70 per CHS deduction model) drives semantic.
  const variant = v >= 85 ? "success" : v >= 70 ? "info" : "destructive";
  return (
    <Badge variant={variant} className={cn("font-medium tabular-nums", className)}>
      {v}
    </Badge>
  );
}
