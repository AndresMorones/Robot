import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

export function OutcomeBadge({
  value,
  className,
}: {
  value: string | null | undefined;
  className?: string;
}) {
  if (!value) {
    return (
      <Badge variant="outline" className={cn("font-normal", className)}>
        —
      </Badge>
    );
  }
  const v = value.toLowerCase();
  const variant =
    v === "load_booked"
      ? "success"
      : v === "carrier_not_qualified"
        ? "destructive"
        : v === "no_match"
          ? "warning"
          : v === "call_abandoned"
            ? "secondary"
            : "outline";
  return (
    <Badge variant={variant} className={cn("font-medium", className)}>
      {titleCase(value)}
    </Badge>
  );
}
