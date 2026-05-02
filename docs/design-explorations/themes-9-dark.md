# 9 Dark-Mode Theme Palettes — Acme Logistics Carrier-Ops Dashboard

Design exploration drafted 2026-04-30. Deliverable for ops-desk dashboard (Next.js 15 + Tailwind 4 + shadcn/ui + Recharts). Intended as side-by-side palette options for the user to pick one or remix. Each theme is meaningfully different on hue family, temperature, contrast strategy, and mood — not 9 variations of the same hue.

All body-text-on-background contrast ratios verified ≥ 4.5:1 (WCAG AA). Chart palettes (`--chart-1`..`--chart-5`) are kept distinguishable from each other and from the primary accent.

---

## 1. Hangar Steel

**Vibe / inspiration.** Cool brushed-aluminum trading bay; aircraft hangar lit by sodium overheads. Bloomberg terminal calm crossed with industrial freight cold-storage.

| Token | Hex |
|---|---|
| `--background` | `#0B1116` |
| `--surface` | `#121A22` |
| `--surface-elevated` | `#1A2530` |
| `--border` | `#28323D` |
| `--foreground` | `#E6EEF6` |
| `--muted` | `#1A2530` |
| `--muted-foreground` | `#9AA9B8` |
| `--primary` | `#5DA9E9` |
| `--primary-foreground` | `#08111A` |
| `--secondary` | `#3D4D5C` |
| `--accent` | `#7FCBFF` |
| `--success` | `#3DDC97` |
| `--warning` | `#F5B14C` |
| `--danger` | `#FF6B6B` |
| `--chart-1` | `#5DA9E9` |
| `--chart-2` | `#7FCBFF` |
| `--chart-3` | `#3DDC97` |
| `--chart-4` | `#F5B14C` |
| `--chart-5` | `#B68CFF` |

**Why for ops.** A dispatcher reading rate sheets and CHS histograms for 6 hours at a stretch needs low-saturation chrome that doesn't fight the eye. Cool blues read as machinery and quietness — alarm hues (amber/red) keep their full attention budget because nothing else competes. The aluminum surface stack signals hierarchy at a glance during glance-driven alarm triage.

```css
:root, .dark {
  --background: #0B1116;
  --surface: #121A22;
  --surface-elevated: #1A2530;
  --border: #28323D;
  --foreground: #E6EEF6;
  --muted: #1A2530;
  --muted-foreground: #9AA9B8;
  --primary: #5DA9E9;
  --primary-foreground: #08111A;
  --secondary: #3D4D5C;
  --accent: #7FCBFF;
  --success: #3DDC97;
  --warning: #F5B14C;
  --danger: #FF6B6B;
  --chart-1: #5DA9E9;
  --chart-2: #7FCBFF;
  --chart-3: #3DDC97;
  --chart-4: #F5B14C;
  --chart-5: #B68CFF;
}
```

Swatches: `#0B1116` `#1A2530` `#5DA9E9` `#7FCBFF` `#F5B14C`

---

## 2. Trading Floor Phosphor

**Vibe / inspiration.** Bloomberg / Reuters CRT terminal at 3am — green phosphor on near-black with amber tickers.

| Token | Hex |
|---|---|
| `--background` | `#050A05` |
| `--surface` | `#0B140B` |
| `--surface-elevated` | `#142014` |
| `--border` | `#1F3320` |
| `--foreground` | `#D8FFD8` |
| `--muted` | `#142014` |
| `--muted-foreground` | `#7DAA7D` |
| `--primary` | `#39FF7A` |
| `--primary-foreground` | `#031003` |
| `--secondary` | `#1F3320` |
| `--accent` | `#FFB347` |
| `--success` | `#39FF7A` |
| `--warning` | `#FFB347` |
| `--danger` | `#FF5470` |
| `--chart-1` | `#39FF7A` |
| `--chart-2` | `#FFB347` |
| `--chart-3` | `#5BC0EB` |
| `--chart-4` | `#FF5470` |
| `--chart-5` | `#C7C7C7` |

**Why for ops.** Freight ops resemble a trading desk: rate, lane, urgency, accept/decline. Phosphor green encodes "go / live / booked" pre-attentively, amber encodes "watch / pending", red encodes "broken / declined". A booking dashboard becomes a tape-reader's screen — booked revenue vs. forecast pops without needing labels.

```css
:root, .dark {
  --background: #050A05;
  --surface: #0B140B;
  --surface-elevated: #142014;
  --border: #1F3320;
  --foreground: #D8FFD8;
  --muted: #142014;
  --muted-foreground: #7DAA7D;
  --primary: #39FF7A;
  --primary-foreground: #031003;
  --secondary: #1F3320;
  --accent: #FFB347;
  --success: #39FF7A;
  --warning: #FFB347;
  --danger: #FF5470;
  --chart-1: #39FF7A;
  --chart-2: #FFB347;
  --chart-3: #5BC0EB;
  --chart-4: #FF5470;
  --chart-5: #C7C7C7;
}
```

Swatches: `#050A05` `#39FF7A` `#FFB347` `#5BC0EB` `#FF5470`

---

## 3. Sodium Dock

**Vibe / inspiration.** Logistics orange-noir — refined Drivergo direction. Loading dock at dusk, sodium-vapor lamps over wet asphalt.

| Token | Hex |
|---|---|
| `--background` | `#0F0B08` |
| `--surface` | `#1A130D` |
| `--surface-elevated` | `#241A12` |
| `--border` | `#3A2A1C` |
| `--foreground` | `#F4E9DC` |
| `--muted` | `#241A12` |
| `--muted-foreground` | `#B79880` |
| `--primary` | `#F08A2A` |
| `--primary-foreground` | `#1A0E04` |
| `--secondary` | `#5C3D24` |
| `--accent` | `#FFB36B` |
| `--success` | `#5DBE82` |
| `--warning` | `#F4C45A` |
| `--danger` | `#E25C4F` |
| `--chart-1` | `#F08A2A` |
| `--chart-2` | `#FFB36B` |
| `--chart-3` | `#5DBE82` |
| `--chart-4` | `#5BB1D6` |
| `--chart-5` | `#C58CF0` |

**Why for ops.** Keeps the freight-orange brand association (Schneider, U-Haul, Drivergo) but on warm-brown chrome instead of cold gray, so the orange feels like a lit interior rather than an alert button. Easier on operators reading carrier names and lanes for hours; secondary chart greens and blues stay cool to provide chromatic contrast against booked revenue.

```css
:root, .dark {
  --background: #0F0B08;
  --surface: #1A130D;
  --surface-elevated: #241A12;
  --border: #3A2A1C;
  --foreground: #F4E9DC;
  --muted: #241A12;
  --muted-foreground: #B79880;
  --primary: #F08A2A;
  --primary-foreground: #1A0E04;
  --secondary: #5C3D24;
  --accent: #FFB36B;
  --success: #5DBE82;
  --warning: #F4C45A;
  --danger: #E25C4F;
  --chart-1: #F08A2A;
  --chart-2: #FFB36B;
  --chart-3: #5DBE82;
  --chart-4: #5BB1D6;
  --chart-5: #C58CF0;
}
```

Swatches: `#0F0B08` `#F08A2A` `#FFB36B` `#5DBE82` `#5BB1D6`

---

## 4. Linear Midnight

**Vibe / inspiration.** Linear / Stripe Sigma calm — deep navy with a single warm amber accent. SaaS executive review.

| Token | Hex |
|---|---|
| `--background` | `#0A0F1F` |
| `--surface` | `#101830` |
| `--surface-elevated` | `#17223F` |
| `--border` | `#243056` |
| `--foreground` | `#E8ECF7` |
| `--muted` | `#17223F` |
| `--muted-foreground` | `#8E97B6` |
| `--primary` | `#F2B547` |
| `--primary-foreground` | `#1A1102` |
| `--secondary` | `#3A4A78` |
| `--accent` | `#7AA2FF` |
| `--success` | `#62C593` |
| `--warning` | `#F2B547` |
| `--danger` | `#FF6B7A` |
| `--chart-1` | `#7AA2FF` |
| `--chart-2` | `#F2B547` |
| `--chart-3` | `#62C593` |
| `--chart-4` | `#FF6B7A` |
| `--chart-5` | `#A39BFF` |

**Why for ops.** Navy grounds the screen so the amber primary reads as "the thing that matters" — booked revenue, hot CHS, SLA breach. Mirrors the visual grammar an ops manager already knows from Linear / Vercel / Stripe so onboarding cost is near zero. Six-hour reading comfort is the killer feature here.

```css
:root, .dark {
  --background: #0A0F1F;
  --surface: #101830;
  --surface-elevated: #17223F;
  --border: #243056;
  --foreground: #E8ECF7;
  --muted: #17223F;
  --muted-foreground: #8E97B6;
  --primary: #F2B547;
  --primary-foreground: #1A1102;
  --secondary: #3A4A78;
  --accent: #7AA2FF;
  --success: #62C593;
  --warning: #F2B547;
  --danger: #FF6B7A;
  --chart-1: #7AA2FF;
  --chart-2: #F2B547;
  --chart-3: #62C593;
  --chart-4: #FF6B7A;
  --chart-5: #A39BFF;
}
```

Swatches: `#0A0F1F` `#101830` `#F2B547` `#7AA2FF` `#62C593`

---

## 5. Carbon Press

**Vibe / inspiration.** High-contrast monochrome — Vercel / Nothing / Apple Pro. Pure white-on-black with a single chartreuse accent.

| Token | Hex |
|---|---|
| `--background` | `#000000` |
| `--surface` | `#0A0A0A` |
| `--surface-elevated` | `#141414` |
| `--border` | `#262626` |
| `--foreground` | `#FAFAFA` |
| `--muted` | `#141414` |
| `--muted-foreground` | `#A3A3A3` |
| `--primary` | `#D7FF3C` |
| `--primary-foreground` | `#0A0F00` |
| `--secondary` | `#262626` |
| `--accent` | `#FAFAFA` |
| `--success` | `#A6E22E` |
| `--warning` | `#FFC857` |
| `--danger` | `#FF4D4D` |
| `--chart-1` | `#D7FF3C` |
| `--chart-2` | `#FAFAFA` |
| `--chart-3` | `#FFC857` |
| `--chart-4` | `#FF4D4D` |
| `--chart-5` | `#9FA8DA` |

**Why for ops.** Minimum chrome, maximum data. With only one accent hue, every chartreuse pixel is a deliberate signal — booked, won, target. Black surfaces save OLED-display power on the docked second monitor that dispatchers run. Pairs well with screenshotting / Loom recording for stakeholder review.

```css
:root, .dark {
  --background: #000000;
  --surface: #0A0A0A;
  --surface-elevated: #141414;
  --border: #262626;
  --foreground: #FAFAFA;
  --muted: #141414;
  --muted-foreground: #A3A3A3;
  --primary: #D7FF3C;
  --primary-foreground: #0A0F00;
  --secondary: #262626;
  --accent: #FAFAFA;
  --success: #A6E22E;
  --warning: #FFC857;
  --danger: #FF4D4D;
  --chart-1: #D7FF3C;
  --chart-2: #FAFAFA;
  --chart-3: #FFC857;
  --chart-4: #FF4D4D;
  --chart-5: #9FA8DA;
}
```

Swatches: `#000000` `#141414` `#D7FF3C` `#FAFAFA` `#FFC857`

---

## 6. Fleet Olive

**Vibe / inspiration.** Military / fleet-ops command center. Warm khaki and faded olive with brass accents. C-130 cargo door colors.

| Token | Hex |
|---|---|
| `--background` | `#0E0F09` |
| `--surface` | `#181A11` |
| `--surface-elevated` | `#22251A` |
| `--border` | `#363926` |
| `--foreground` | `#EFE9D2` |
| `--muted` | `#22251A` |
| `--muted-foreground` | `#A8A684` |
| `--primary` | `#C4B454` |
| `--primary-foreground` | `#15140A` |
| `--secondary` | `#4A4D2D` |
| `--accent` | `#D9A441` |
| `--success` | `#7DA84A` |
| `--warning` | `#E0A92F` |
| `--danger` | `#C24A3A` |
| `--chart-1` | `#C4B454` |
| `--chart-2` | `#D9A441` |
| `--chart-3` | `#7DA84A` |
| `--chart-4` | `#6FA3B6` |
| `--chart-5` | `#C24A3A` |

**Why for ops.** Freight fleet management is fundamentally a logistics-of-iron job — the military aesthetic resonates with carrier-side dispatchers who came up around DoT and DOT-equivalent fleet ops. Olive surfaces feel "rugged" without being cartoonish; brass primary picks out rate-target highlights. Distinctive enough that an ops desk recognizes its own dashboard from across the room.

```css
:root, .dark {
  --background: #0E0F09;
  --surface: #181A11;
  --surface-elevated: #22251A;
  --border: #363926;
  --foreground: #EFE9D2;
  --muted: #22251A;
  --muted-foreground: #A8A684;
  --primary: #C4B454;
  --primary-foreground: #15140A;
  --secondary: #4A4D2D;
  --accent: #D9A441;
  --success: #7DA84A;
  --warning: #E0A92F;
  --danger: #C24A3A;
  --chart-1: #C4B454;
  --chart-2: #D9A441;
  --chart-3: #7DA84A;
  --chart-4: #6FA3B6;
  --chart-5: #C24A3A;
}
```

Swatches: `#0E0F09` `#C4B454` `#D9A441` `#7DA84A` `#6FA3B6`

---

## 7. Neon Foundry

**Vibe / inspiration.** Carbon + magenta cyber-bold. Datadog meets Synthwave; midnight server rack lit by hot-pink edge LEDs.

| Token | Hex |
|---|---|
| `--background` | `#080611` |
| `--surface` | `#0F0C1E` |
| `--surface-elevated` | `#16122B` |
| `--border` | `#2A2244` |
| `--foreground` | `#F1E9FF` |
| `--muted` | `#16122B` |
| `--muted-foreground` | `#9A8FBE` |
| `--primary` | `#FF2E9A` |
| `--primary-foreground` | `#1A0510` |
| `--secondary` | `#3A2E66` |
| `--accent` | `#00E5FF` |
| `--success` | `#3CE3A3` |
| `--warning` | `#FFD23F` |
| `--danger` | `#FF4D6D` |
| `--chart-1` | `#FF2E9A` |
| `--chart-2` | `#00E5FF` |
| `--chart-3` | `#3CE3A3` |
| `--chart-4` | `#FFD23F` |
| `--chart-5` | `#9D7BFF` |

**Why for ops.** When a take-home demo needs to feel different in the first 3 seconds — this is it. The magenta + cyan duo encodes booked vs. negotiating across stacked-bar charts more crisply than any naturalistic palette. Bold enough that flagged-call lists and sentiment splits visually pop on a Loom recording. Mood: this team ships.

```css
:root, .dark {
  --background: #080611;
  --surface: #0F0C1E;
  --surface-elevated: #16122B;
  --border: #2A2244;
  --foreground: #F1E9FF;
  --muted: #16122B;
  --muted-foreground: #9A8FBE;
  --primary: #FF2E9A;
  --primary-foreground: #1A0510;
  --secondary: #3A2E66;
  --accent: #00E5FF;
  --success: #3CE3A3;
  --warning: #FFD23F;
  --danger: #FF4D6D;
  --chart-1: #FF2E9A;
  --chart-2: #00E5FF;
  --chart-3: #3CE3A3;
  --chart-4: #FFD23F;
  --chart-5: #9D7BFF;
}
```

Swatches: `#080611` `#FF2E9A` `#00E5FF` `#3CE3A3` `#FFD23F`

---

## 8. Harbor Teal

**Vibe / inspiration.** Modern fintech — Stripe + Plaid + Mercury banking dark mode. Slate hull with cool teal running lights.

| Token | Hex |
|---|---|
| `--background` | `#0C1418` |
| `--surface` | `#131E24` |
| `--surface-elevated` | `#1B2A33` |
| `--border` | `#2C3F4A` |
| `--foreground` | `#E6F1F4` |
| `--muted` | `#1B2A33` |
| `--muted-foreground` | `#92A8B2` |
| `--primary` | `#2DD4BF` |
| `--primary-foreground` | `#04201C` |
| `--secondary` | `#385664` |
| `--accent` | `#7DD3FC` |
| `--success` | `#34D399` |
| `--warning` | `#FBBF24` |
| `--danger` | `#FB7185` |
| `--chart-1` | `#2DD4BF` |
| `--chart-2` | `#7DD3FC` |
| `--chart-3` | `#FBBF24` |
| `--chart-4` | `#FB7185` |
| `--chart-5` | `#A78BFA` |

**Why for ops.** Freight is dollars per mile — financial reading bias is correct. Teal primary signals "money" without the green-vs-red overload (those stay reserved for booked vs. lost). Cool slate hull is gentle for long sessions; KPI sparklines and revenue lines feel like a treasury page rather than a CRUD admin panel.

```css
:root, .dark {
  --background: #0C1418;
  --surface: #131E24;
  --surface-elevated: #1B2A33;
  --border: #2C3F4A;
  --foreground: #E6F1F4;
  --muted: #1B2A33;
  --muted-foreground: #92A8B2;
  --primary: #2DD4BF;
  --primary-foreground: #04201C;
  --secondary: #385664;
  --accent: #7DD3FC;
  --success: #34D399;
  --warning: #FBBF24;
  --danger: #FB7185;
  --chart-1: #2DD4BF;
  --chart-2: #7DD3FC;
  --chart-3: #FBBF24;
  --chart-4: #FB7185;
  --chart-5: #A78BFA;
}
```

Swatches: `#0C1418` `#2DD4BF` `#7DD3FC` `#FBBF24` `#FB7185`

---

## 9. Pine Ledger

**Vibe / inspiration.** Forest green + cream — natural / financial. Old-money accounting house; private bank annual report bound in green leather.

| Token | Hex |
|---|---|
| `--background` | `#0A1410` |
| `--surface` | `#0F1E18` |
| `--surface-elevated` | `#162B22` |
| `--border` | `#264236` |
| `--foreground` | `#F1EBDC` |
| `--muted` | `#162B22` |
| `--muted-foreground` | `#A8B0A0` |
| `--primary` | `#7FB069` |
| `--primary-foreground` | `#0B1606` |
| `--secondary` | `#395B45` |
| `--accent` | `#E8C97C` |
| `--success` | `#7FB069` |
| `--warning` | `#E8C97C` |
| `--danger` | `#C45B4D` |
| `--chart-1` | `#7FB069` |
| `--chart-2` | `#E8C97C` |
| `--chart-3` | `#6BA8C4` |
| `--chart-4` | `#C45B4D` |
| `--chart-5` | `#B89AC4` |

**Why for ops.** A booking-ops desk is essentially a P&L screen. Forest + cream encodes "money in, money out" with cultural weight that pure-tech palettes lack — feels expensive, considered, durable. Cream foreground (`#F1EBDC`) reduces the harsh white-on-black flare on long shifts. Brass accent reserves itself for "this number is the one to watch." Stands out hard from the other 8.

```css
:root, .dark {
  --background: #0A1410;
  --surface: #0F1E18;
  --surface-elevated: #162B22;
  --border: #264236;
  --foreground: #F1EBDC;
  --muted: #162B22;
  --muted-foreground: #A8B0A0;
  --primary: #7FB069;
  --primary-foreground: #0B1606;
  --secondary: #395B45;
  --accent: #E8C97C;
  --success: #7FB069;
  --warning: #E8C97C;
  --danger: #C45B4D;
  --chart-1: #7FB069;
  --chart-2: #E8C97C;
  --chart-3: #6BA8C4;
  --chart-4: #C45B4D;
  --chart-5: #B89AC4;
}
```

Swatches: `#0A1410` `#7FB069` `#E8C97C` `#6BA8C4` `#C45B4D`

---

## Side-by-side hue strategy summary

| # | Theme | Hue family | Temperature | Primary accent | Mood |
|---|---|---|---|---|---|
| 1 | Hangar Steel | Cool blue | Cold | `#5DA9E9` | Industrial, calm |
| 2 | Trading Floor Phosphor | Phosphor green | Warm-cool mix | `#39FF7A` | Tape-reader urgency |
| 3 | Sodium Dock | Warm orange-brown | Warm | `#F08A2A` | Loading-dock dusk |
| 4 | Linear Midnight | Navy + amber | Cool body, warm accent | `#F2B547` | SaaS executive |
| 5 | Carbon Press | Pure mono + chartreuse | Neutral | `#D7FF3C` | Editorial minimal |
| 6 | Fleet Olive | Olive / brass | Warm | `#C4B454` | Military fleet ops |
| 7 | Neon Foundry | Magenta + cyan | Hot | `#FF2E9A` | Cyber bold |
| 8 | Harbor Teal | Slate + teal | Cool | `#2DD4BF` | Modern fintech |
| 9 | Pine Ledger | Forest + cream | Warm-cool balance | `#7FB069` | Old-money ledger |

---

## Notes for adoption

- Drop the chosen `:root, .dark` block into `dashboard/src/app/globals.css` replacing the current dark-mode token set. shadcn/ui consumes `--background`, `--foreground`, `--primary`, `--secondary`, `--accent`, `--muted`, `--muted-foreground`, `--border`, `--destructive` (alias to `--danger`) by default; the extra `--surface`, `--surface-elevated`, `--success`, `--warning`, `--chart-1..5` tokens cover Recharts and KPI cards.
- If `--destructive` is required by current shadcn config: alias `--destructive: var(--danger);` and `--destructive-foreground: #FFFFFF;` in the same block.
- Recharts pulls colors directly from inline strings or CSS vars — pass `var(--chart-1)` etc. through a small helper rather than hex literals so theme switching is atomic.
- All foreground/background pairs hand-checked at ≥ 4.5:1; adjust `--muted-foreground` upward by ~5% if your bar-chart axis labels still feel faint at small sizes (especially in themes 2, 6, 9 where muted leans warm).
