// Signed-link auth middleware for the dashboard.
//
// Token format: `{exp_unix_seconds}.{hmac_sha256_hex}` where the HMAC is over
// the exp string using LINK_SIGNING_SECRET.
//
// First request: provide `?t=<exp>.<sig>` query param. Middleware validates,
// sets an httpOnly auth cookie, and redirects to the clean URL (no token in
// browser history beyond the first click).
//
// Subsequent navigation: cookie carries the token. No need for ?t= every time.
//
// Generate links via `scripts/generate_signed_link.py` (server-side; uses the
// same secret).
//
// Edge runtime: uses Web Crypto (crypto.subtle), not Node's `crypto` module.

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SECRET = process.env.LINK_SIGNING_SECRET ?? "";
const COOKIE_NAME = "dash_auth";

function hexFromBuffer(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function hmacHex(secret: string, message: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return hexFromBuffer(sig);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

async function isValidToken(token: string | null | undefined): Promise<boolean> {
  if (!token || !SECRET) return false;
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [exp, sig] = parts;
  const expNum = Number(exp);
  if (!Number.isInteger(expNum) || expNum <= 0) return false;
  if (Date.now() / 1000 > expNum) return false;
  const expected = await hmacHex(SECRET, exp);
  return timingSafeEqual(sig, expected);
}

export async function middleware(req: NextRequest) {
  // Local dev convenience: blank LINK_SIGNING_SECRET disables enforcement.
  // Production deploys MUST set this; leaving it blank in production is a misconfiguration
  // that we treat as fail-open here (dev-friendly) — Fly secret sync is the prod safeguard.
  if (!SECRET) return NextResponse.next();

  const url = req.nextUrl;
  const queryToken = url.searchParams.get("t");
  const cookieToken = req.cookies.get(COOKIE_NAME)?.value;

  const queryOk = await isValidToken(queryToken);
  const cookieOk = await isValidToken(cookieToken);

  // Successful URL-token entry: set cookie, scrub the token from URL.
  if (queryOk && queryToken) {
    const cleanUrl = url.clone();
    cleanUrl.searchParams.delete("t");
    const res = NextResponse.redirect(cleanUrl);
    const expSec = Number(queryToken.split(".")[0]);
    const maxAge = Math.max(0, expSec - Math.floor(Date.now() / 1000));
    res.cookies.set(COOKIE_NAME, queryToken, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge,
    });
    return res;
  }

  if (cookieOk) {
    return NextResponse.next();
  }

  return new NextResponse(
    "Access requires a valid signed link. Contact the operator for a new link.",
    {
      status: 401,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    },
  );
}

// Skip middleware for: Next.js internals, static assets, /api/* (incl. health), public files.
// CRITICAL: /api/health must be reachable for Fly's HTTP healthcheck — otherwise
// the middleware would 401 the healthcheck and Fly would restart the machine in a loop.
export const config = {
  matcher: ["/((?!api/|_next/|favicon|robots.txt|sitemap.xml|.*\\.(?:png|jpg|jpeg|gif|svg|webp|ico|css|js|woff2?|ttf)).*)"],
};
