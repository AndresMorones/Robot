"use client";

import { useEffect, useState } from "react";

import { CmdKPalette } from "./cmdk-palette";

// Root-level provider — owns open state, registers global ⌘K / Ctrl-K + Esc
// listener. Mounted once in app/layout.tsx so the palette works on every route.
export function CmdKProvider() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") {
        setOpen((o) => (o ? false : o));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return <CmdKPalette open={open} onOpenChange={setOpen} />;
}
