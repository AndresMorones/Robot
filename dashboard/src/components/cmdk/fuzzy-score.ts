// Tiny fuzzy scorer — substring + start-of-word + acronym + subsequence.
// Pure, no deps. Higher is better; <= 0 means no match.
//
// Score scale (rough):
//   1000 — exact
//    600 — prefix
//    400 — start-of-word hit (e.g. "ne" in "New Bookings")
//    300 — acronym hit (e.g. "nb" in "New Bookings")
//    200 — substring contained
//     50 — in-order subsequence (loose)
//      0 — no match
export function fuzzyScore(haystack: string, needle: string): number {
  if (!needle) return 1;
  const h = haystack.toLowerCase();
  const n = needle.toLowerCase();
  if (h === n) return 1000;
  if (h.startsWith(n)) return 600;
  // Start-of-word: match needle against any word boundary.
  const words = h.split(/[\s_\-./]+/).filter(Boolean);
  if (words.some((w) => w.startsWith(n))) return 400;
  // Acronym: take first char of each word, see if needle is a prefix.
  const acronym = words.map((w) => w[0] ?? "").join("");
  if (acronym.startsWith(n)) return 300;
  if (h.includes(n)) return 200;
  // Loose subsequence — every char of n appears in order in h.
  let i = 0;
  for (let k = 0; k < h.length && i < n.length; k++) if (h[k] === n[i]) i++;
  return i === n.length ? 50 : 0;
}
