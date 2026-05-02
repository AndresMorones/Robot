"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// Hand-rolled toggle group (~20 LOC of logic). Used for percentile multi-select
// + time-range chips on the Telemetry tab. Avoids adding @radix-ui/react-toggle
// per ADR-011's library-minimization rule.

type ToggleGroupContextValue = {
  value: string[];
  onChange: (next: string[]) => void;
  type: "single" | "multiple";
};

const ToggleGroupContext = React.createContext<ToggleGroupContextValue | null>(
  null,
);

export interface ToggleGroupProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "onChange"> {
  type?: "single" | "multiple";
  value: string[];
  onChange: (next: string[]) => void;
}

export function ToggleGroup({
  type = "multiple",
  value,
  onChange,
  className,
  children,
  ...rest
}: ToggleGroupProps) {
  return (
    <ToggleGroupContext.Provider value={{ value, onChange, type }}>
      <div
        role="group"
        className={cn(
          "inline-flex items-center gap-1 rounded-md border border-border bg-card p-0.5 text-xs",
          className,
        )}
        {...rest}
      >
        {children}
      </div>
    </ToggleGroupContext.Provider>
  );
}

export interface ToggleGroupItemProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

export function ToggleGroupItem({
  value,
  className,
  children,
  ...rest
}: ToggleGroupItemProps) {
  const ctx = React.useContext(ToggleGroupContext);
  if (!ctx) {
    throw new Error("ToggleGroupItem must be inside ToggleGroup");
  }
  const active = ctx.value.includes(value);
  const onClick = () => {
    if (ctx.type === "single") {
      ctx.onChange(active ? [] : [value]);
      return;
    }
    ctx.onChange(active ? ctx.value.filter((v) => v !== value) : [...ctx.value, value]);
  };
  return (
    <button
      type="button"
      role={ctx.type === "single" ? "radio" : "checkbox"}
      aria-checked={active}
      onClick={onClick}
      className={cn(
        "inline-flex h-6 items-center justify-center rounded-sm px-2 text-[11px] font-medium tabular-nums transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-secondary hover:text-foreground",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
