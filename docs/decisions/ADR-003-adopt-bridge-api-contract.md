# ADR-003 — Adopt HR Bridge API contract for our FastAPI + loads/carriers schema

- **Status**: Proposed (Tier-2 — implement after MVP demo ships)
- **Date**: 2026-04-25
- **Decided by**: Andres + Claude (after Andres surfaced the Bridge API docs mid-build)

## Context

We've been building our FastAPI's loads/calls endpoints from scratch — custom shapes, custom field names. Today Andres surfaced HR's **Bridge API** contract: a STANDARD shape HR uses to integrate with real broker TMS systems.

The Bridge API has two halves:

**"HappyRobot calls your API"** (you implement, HR consumes):
- `GET /api/v1/loads` — search loads (max 3 results, supports lat/lng/radius + temp filters)
- `GET /api/v1/loads/{load_id}` — get single load
- `GET /api/v1/carriers/find?mc=...&dot=...` — look up carrier (proxy to FMCSA + your cache)
- `POST /api/v1/offers/log` — log a carrier's price offer

**"Call HappyRobot API"** (HR implements, you consume):
- `POST /api/v1/loads` — `event_type: load_upsert` — push your TMS loads to HR
- `POST /api/v1/carriers` — `event_type: carrier_upsert` — push carrier records to HR

The shapes are richer than what we built — they include fields we omitted that materially affect the voice agent's decisions: `max_buy` (explicit per-load negotiation floor), `is_hazmat`, `is_team_required`, multi-stop `stops` arrays, `min_temp`/`max_temp` reefer ranges, `cargo_value`, broker `branch`/`team` attribution, structured `contacts`.

## Decision

**Adopt the Bridge API contract for our FastAPI as a Tier-2 deliverable.** Not for MVP — MVP ships with current Twin-native architecture (Read-from-Twin nodes, custom dashboard endpoints). Tier-2 layers Bridge-shaped endpoints on top.

### What changes

#### 1. Loads table schema — add Bridge-aligned fields

Current loads table (15 cols) becomes 25 cols:

```sql
ALTER TABLE loads ADD COLUMN max_buy DOUBLE PRECISION;             -- explicit floor per load
ALTER TABLE loads ADD COLUMN status TEXT DEFAULT 'available';      -- available/covered/etc.
ALTER TABLE loads ADD COLUMN is_partial BOOLEAN DEFAULT FALSE;
ALTER TABLE loads ADD COLUMN is_hazmat BOOLEAN DEFAULT FALSE;
ALTER TABLE loads ADD COLUMN is_team_required BOOLEAN DEFAULT FALSE;
ALTER TABLE loads ADD COLUMN min_temp DOUBLE PRECISION;            -- reefer range
ALTER TABLE loads ADD COLUMN max_temp DOUBLE PRECISION;
ALTER TABLE loads ADD COLUMN cargo_value DOUBLE PRECISION;
ALTER TABLE loads ADD COLUMN branch TEXT;                          -- broker office attribution
ALTER TABLE loads ADD COLUMN contact_name TEXT;
ALTER TABLE loads ADD COLUMN contact_phone TEXT;
```

Skipped (operational/specialist, low voice-agent relevance):
- `bol_number`, `trailer_number`, `truck_number`, `pickup_number`, `po_number` — TMS internals
- `un_number`, `package_group`, `hazmat_class` — specialist hazmat (covered by `is_hazmat` flag for now)
- `team` (vs `branch`), `contacts.email`, `contacts.extension`, `contacts.type` — granular org details

Optional (Tier-3 if multi-stop becomes common):
- `stops` JSONB column — multi-stop sequences. Currently every load is 2-stop (origin → destination); if we need true multi-stop, store as JSONB.

#### 1.5. FMCSA response is RICHER than the 7-field AND-gate uses

Probed the take-home FMCSA endpoint live (2026-04-25) against MC 250819 — 40+ fields are returned, far beyond the 7 we use for eligibility. Catalog of what's actually available:

**Identity + authority (used today, 9 fields):** `legalName`, `dbaName`, `dotNumber`, `mcNumber`, `ein`, `allowedToOperate`, `statusCode`, `commonAuthorityStatus`, `contractAuthorityStatus`, `brokerAuthorityStatus`.

**Operation classification (used today, 4 fields):** `carrierOperation.carrierOperationCode`, `carrierOperation.carrierOperationDesc`, `censusTypeId.censusType`, `isPassengerCarrier`.

**Safety profile (1 used, 6 unused):** `safetyRating` ✓ used. NOT used yet: `safetyRatingDate`, `safetyReviewDate`, `safetyReviewType`, `reviewDate`, `reviewType`, `mcs150Outdated`, `snapshotDate`, `oosDate` (latter ✓ used in AND-gate).

**Inspection + OOS rates (none used, 12 fields available):**
- `driverInsp`, `driverOosInsp`, `driverOosRate`, `driverOosRateNationalAverage`
- `vehicleInsp`, `vehicleOosInsp`, `vehicleOosRate`, `vehicleOosRateNationalAverage`
- `hazmatInsp`, `hazmatOosInsp`, `hazmatOosRate`, `hazmatOosRateNationalAverage`

**Crash history (none used, 4 fields):** `crashTotal`, `fatalCrash`, `injCrash`, `towawayCrash`.

**Insurance compliance (none used, 6 fields):** `bipdInsuranceOnFile` (Bodily Injury & Property Damage, in $1000s), `bipdInsuranceRequired`, `bipdRequiredAmount`, `bondInsuranceOnFile`, `bondInsuranceRequired`, `cargoInsuranceOnFile`, `cargoInsuranceRequired`.

**Physical address (none used, 5 fields):** `phyCity`, `phyState`, `phyZipcode`, `phyStreet`, `phyCountry`.

**Fleet size (none used, 2 fields):** `totalDrivers`, `totalPowerUnits`.

**Other (1 unused):** `issScore` (Inspection Selection System risk score).

### Tier-2 use cases for the unused fields

| FMCSA field | Use case for our agent | Where it lands |
|---|---|---|
| `bipdInsuranceOnFile`, `bipdRequiredAmount` | "Carrier insurance compliance" gate — refuse carriers with BIPD < $750K | New AND-gate rule; `carriers.bipd_insurance_on_file` column |
| `vehicleOosRate` vs national avg | Risk score: out-of-service rate above national avg → log warning, optionally route to specialist | `carriers.vehicle_oos_rate`, dashboard "high-risk carriers" view |
| `crashTotal`, `fatalCrash` | Decline carriers with ≥1 fatal crash by default; configurable threshold | `carriers.fatal_crash_count`; new gate rule |
| `phyCity`, `phyState` | Anti-fraud: caller-claimed origin lane vs FMCSA address mismatch heuristic | Voice agent audit hook; `calls_log.fmcsa_address_match BOOLEAN` |
| `totalDrivers`, `totalPowerUnits` | Fleet size profile (1-truck operator vs 50-truck) — affects rate negotiation strategy | Negotiate v2 sidecar input; `carriers.total_power_units` |
| `issScore` | High-level risk score (FMCSA-computed); roll into our own carrier risk tier | `carriers.iss_score` |

Updating the **carriers table schema** in §2 to capture the high-value subset.

Bridge API has a `GET /carriers/find?mc=...&dot=...` endpoint and a `POST /carriers` upsert. We don't have a carriers table in Twin yet; one is needed:

```sql
CREATE TABLE carriers (
  carrier_id TEXT PRIMARY KEY,                  -- internal UUID
  mc_number TEXT UNIQUE NOT NULL,
  dot_number TEXT,
  ein TEXT,
  legal_name TEXT,
  dba_name TEXT,
  status TEXT DEFAULT 'in_review',              -- active/fail/inactive/in_review/not_set

  -- FMCSA eligibility (used in AND-gate today)
  fmcsa_allowed_to_operate TEXT,                -- Y/N
  fmcsa_status_code TEXT,                       -- A/I/R
  fmcsa_safety_rating TEXT,                     -- Satisfactory/Conditional/Unsatisfactory/null
  fmcsa_carrier_operation_code TEXT,            -- A/B/C
  fmcsa_oos_date TIMESTAMPTZ,
  fmcsa_broker_authority_status TEXT,
  fmcsa_common_authority_status TEXT,

  -- FMCSA risk profile (Tier-2 — newly surfaced)
  fmcsa_crash_total INT,
  fmcsa_fatal_crash INT,
  fmcsa_inj_crash INT,
  fmcsa_towaway_crash INT,
  fmcsa_driver_oos_rate DOUBLE PRECISION,
  fmcsa_vehicle_oos_rate DOUBLE PRECISION,
  fmcsa_hazmat_oos_rate DOUBLE PRECISION,
  fmcsa_iss_score DOUBLE PRECISION,

  -- FMCSA insurance compliance (Tier-2)
  fmcsa_bipd_on_file INT,                       -- in $1000s; ≥750 = $750K minimum compliant
  fmcsa_cargo_on_file INT,
  fmcsa_bond_on_file INT,

  -- FMCSA fleet size (Tier-2)
  fmcsa_total_drivers INT,
  fmcsa_total_power_units INT,

  -- FMCSA address (Tier-2 anti-fraud)
  fmcsa_phy_city TEXT,
  fmcsa_phy_state TEXT,
  fmcsa_phy_zipcode TEXT,

  -- Cache + history
  fmcsa_last_verified TIMESTAMPTZ,
  contact_name TEXT,
  contact_phone TEXT,
  contact_email TEXT,
  preferred_lanes JSONB,                        -- markets array from Bridge spec
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_carriers_mc ON carriers (mc_number);
CREATE INDEX idx_carriers_dot ON carriers (dot_number);
CREATE INDEX idx_carriers_status ON carriers (status);
CREATE INDEX idx_carriers_safety_rating ON carriers (fmcsa_safety_rating);
```

Use cases:
- Cache FMCSA verify_carrier results (avoid re-hitting FMCSA on every call)
- Build carrier history for the voice agent ("we've worked with you on Dallas-Atlanta before")
- `GET /api/v1/carriers/find` reads from this table; falls back to FMCSA if MC unknown
- Future: feed `preferred_lanes` into negotiate_evaluate as a leverage signal

#### 3. Offers table — NEW

Bridge API has `POST /api/v1/offers/log`. We don't have an offers table; one tracks every carrier counter offer:

```sql
CREATE TABLE offers (
  id BIGSERIAL PRIMARY KEY,
  call_id TEXT NOT NULL,
  load_id TEXT NOT NULL,
  mc_number TEXT NOT NULL,
  carrier_offer DOUBLE PRECISION NOT NULL,
  round_number INT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_offers_call ON offers (call_id);
CREATE INDEX idx_offers_mc ON offers (mc_number);
CREATE INDEX idx_offers_load ON offers (load_id);
```

Use case:
- Negotiation history per carrier — feed into negotiate_evaluate v2 (`carrier_avg_agreed_discount_pct`, `carrier_aggressive_negotiator_flag`)
- Dashboard: "carriers who hammer the most rounds before booking"
- Replay debugging: trace exactly what offers were exchanged in a call

#### 4. FastAPI endpoint surface — adopt Bridge contract

Current endpoints (custom shape):
- `GET /v1/loads/{reference_number}` — keep, alias to Bridge path
- `GET /v1/loads/search?origin_state=&destination_state=&equipment_type=` — refactor to Bridge contract
- `POST /v1/calls/log` — keep (deprecated by Write-to-Twin but stays as backwards-compat shim)
- `GET /v1/dashboard/{funnel,economics,operational,quality}` — keep, custom dashboard shape

New endpoints (Bridge contract):
- `GET /api/v1/loads` — Bridge search (city/state/equipment/lat-lng-radius/temp/pickup_date filters)
- `GET /api/v1/loads/{load_id}` — Bridge single-load
- `GET /api/v1/carriers/find?mc=&dot=` — proxy to FMCSA SAFER (using `FMCSA_WEB_KEY`) + cache to Twin's carriers table
- `POST /api/v1/offers/log` — append to Twin's offers table

#### 5. FMCSA integration — wrap the take-home-provided key for caching + audit

**Correction 2026-04-25:** the take-home brief provides the FMCSA key directly (currently `cdc33e44d693a3a58451898d4ec9df862c65b954`, used in `verify_carrier`'s webhook child). No need to procure a separate one from QCMobile portal — that's not a Tier-2 step, that's just "the key you were given."

What Tier-2 actually adds is a **caching + audit wrapper** around the same key:

`verify_carrier` calls `GET /api/v1/carriers/find?mc=...` against our FastAPI. Our FastAPI:
1. Queries our Twin `carriers` table — if `fmcsa_last_verified` < 24h ago, return cached
2. Otherwise calls FMCSA SAFER with the same `FMCSA_WEB_KEY` (loaded from Fly secret)
3. Upserts result to Twin `carriers`
4. Returns Bridge-shaped response

Benefits (still real, just not "we got our own key"):
- 24-hour cache eliminates redundant FMCSA calls when same MC repeats in a day
- Audit trail of every lookup in our DB (compliance-friendly)
- Rate-limit insulation if FMCSA gets cranky
- Surfaces caller stats in dashboard ("most-verified MCs", "FMCSA hit rate")

`FMCSA_WEB_KEY` continues to mean "the take-home-issued key" — same value, just propagated as a Fly secret instead of hardcoded in the HR webhook URL.

#### 6. Heat function — how `max_buy` gets dynamically tuned per load

The Bridge API spec says `max_buy` is data per load. Question: who sets it, and how does it move as the world changes?

**Three sources, layered:**

**Layer 1 — broker-authored (initial post).** When a load enters the system (CSV seed, `POST /api/v1/loads` upsert from a real broker's TMS, or manual entry), `max_buy` defaults to `loadboard_rate × 0.90`. Broker can override per-load if they have pricing intelligence we don't (e.g., "this lane runs hot in Q2, set max_buy = loadboard_rate"). Stored as the value in the `loads.max_buy` column.

**Layer 2 — computed mid-call by `negotiate_evaluate` Python sidecar.** The sidecar (currently v1 deterministic floor) gets a v2 upgrade that ingests load metadata + current time, computes `effective_max_buy`, and uses it as the hard floor in place of the workflow-variable percentage.

Why the sidecar (not the API endpoint):
- Sidecar already takes `loadboard_rate, round_number, carrier_offer, prior_broker_offers` — adding `pickup_datetime, posted_at, is_hazmat, is_team_required` is a natural extension of the same surface.
- `now` is wall-clock at decision time — the sidecar runs mid-call, the API endpoint runs at search time (could be minutes earlier; matters less but the sidecar is the canonical decision point).
- Negotiation policy belongs to the negotiation engine, not the load-fetch layer. Cleaner separation.
- Sidecar v2 was already on the roadmap to add personas + sentiment + history; heat is the same shape of extension.

```python
# negotiate_evaluate v2 sketch — heat function inside the sidecar
def compute_effective_max_buy(load, now, base_floor_pct):
    """
    Deterministic heat-adjusted floor. Multipliers are PLACEHOLDERS — final
    values to be tuned with broker input post-MVP. The structure is locked;
    the numbers are TBD.
    """
    base = load.get("max_buy") or load["loadboard_rate"] * (1 - base_floor_pct)
    multiplier = 1.0

    hours_until_pickup = (load["pickup_datetime"] - now).total_seconds() / 3600
    hours_since_posted = (now - load["posted_at"]).total_seconds() / 3600

    # Urgency premium — broker pays more for last-minute clears
    if hours_until_pickup < 12:
        multiplier += URGENCY_PREMIUM_HIGH      # TBD
    elif hours_until_pickup < 24:
        multiplier += URGENCY_PREMIUM_MED       # TBD

    # Specialty premium — smaller carrier pool
    if load.get("is_hazmat") or load.get("is_team_required"):
        multiplier += SPECIALTY_PREMIUM         # TBD

    # Stale discount — broker squeezes when load sits
    if hours_since_posted > 48 and hours_until_pickup > 48:
        multiplier -= STALE_DISCOUNT_HIGH       # TBD
    elif hours_since_posted > 24 and hours_until_pickup > 24:
        multiplier -= STALE_DISCOUNT_MED        # TBD

    # Bound: never exceed loadboard, never floor below MIN_FLOOR_PCT
    effective = base * multiplier
    return max(load["loadboard_rate"] * MIN_FLOOR_PCT, min(load["loadboard_rate"], effective))
```

Multiplier values (`URGENCY_PREMIUM_HIGH`, `STALE_DISCOUNT_HIGH`, etc.) are intentionally **TBD** — final numbers come from broker tuning post-MVP. Direction + signal set is the locked design; magnitudes are knobs.

The function is fully deterministic — no ML, no historical data dependency. Three signal classes from the load itself drive it: time-to-pickup, posted-age, specialty flags. Explainable to broker pricing managers; tunable via constants at the top of the sidecar OR as workflow variables for hot-reload.

**Tunable via workflow variables (Tier-2.5 enhancement).** The 5 multiplier constants could promote to HR workflow variables (`urgency_premium_high_pct`, etc.) — broker pricing manager edits them in HR UI, no code redeploy needed. Same pattern as `negotiation_floor_pct` today.

**Layer 3 — pricing model (Tier-3, future R&D).** ML model trained on historical accept/reject + outcome data: predicts the highest max_buy at which the load books in <X hours. Not in scope here.

**Schema implication:** loads table needs a `posted_at TIMESTAMPTZ` column for Layer 2 to work. Adding it to the §1 ALTER block:

```sql
ALTER TABLE loads ADD COLUMN posted_at TIMESTAMPTZ DEFAULT NOW();
```

For seed data, backfill `posted_at` to a value 0–24 hours before the earliest pickup_datetime to simulate fresh-vs-stale variation across the 25 loads. This means our 25 demo loads will exhibit realistic heat variation when the voice agent searches mid-call.

**What we explicitly skip for MVP heat (acknowledged Tier-2/3):**
- **Lane heat** ("Dallas-Atlanta is in high demand right now") — needs market data we don't have. Synthesizing it from our own `calls_log` history is a Tier-3 once we have meaningful booking volume.
- **Carrier-specific heat** ("this MC accepts skinny margins on Tuesdays") — Tier-3 personalization layer; needs offers + carriers history populated first.
- **Real-time spot market integration** (DAT, Truckstop) — out of scope; would need a separate data integration.
- **Cargo-value-based heat** — high `cargo_value` could justify margin compression, but the signal is noisy without broker risk-tolerance data. Defer.

#### 7. calls_log additions — KEEP MINIMAL FOR MVP

Bridge API surfaces additional fields we COULD capture in calls_log:
- `dot_number`, `legal_name` — from `verify_carrier` response. Already in canonical Extract schema (Tier-2 deferred).
- `is_hazmat`, `is_team_required` — from load. NULL for declined calls; informational for booked calls.
- `branch` — broker office handling the call. Useful for multi-broker SaaS.
- `cargo_value` — high-value freight signal.

**Recommendation:** none of these block MVP. Computed/derived fields (`rate_per_mile`, `gap_to_max_buy_pct`, `savings_vs_loadboard_pct`) live in dashboard SQL, not calls_log columns — keeps the table thin.

For Tier-2 parity with Bridge, after the carrier+offers tables exist:
- Add `calls_log.carrier_id` (FK to carriers.carrier_id) — once carriers table is populated
- Add `calls_log.max_buy_at_call_time` — snapshot of the load's max_buy when the call happened (loads.max_buy can change later)

## Rationale

- **Industry-standard contract** — adopting Bridge API means any future broker swapping us out for their TMS gets a drop-in replacement. Strong FDE-grade signal in broker-doc.
- **Voice-agent prompts likely already speak this dialect** — HR ships voice-agent templates that consume the Bridge contract. Our extensions (negotiate_evaluate, custom Prompt) integrate cleaner if our API speaks the same language.
- **`max_buy` per load is the missing piece** — we've been computing the floor as `loadboard_rate × (1 - negotiation_floor_pct)` everywhere. The Bridge contract treats max_buy as data, not derived. Storing it explicitly per load means each load can have a different floor (e.g., a hot load gets max_buy=loadboard_rate; a stale load gets max_buy=loadboard_rate*0.85). Dramatically more flexible than a single workflow variable.
- **carriers table unlocks history** — negotiation v2 + dashboard "repeat carrier" insights need this. No way to do it without a carriers table in our store.
- **offers table unlocks debugging** — when a call goes weird, having every counter-offer in a queryable table beats grepping transcripts.
- **FMCSA caching saves money + latency** — at 50 calls/day we hit FMCSA 50× redundantly under HR demo. With our cache, ~5×. At 5K calls/day the savings compound.
- **Defer to Tier-2 because MVP doesn't need it** — Andres ships the demo first; this lands afterwards on the same `iac` branch (or a sibling `bridge-api` branch) when there's time to refactor cleanly.

## Implementation order (Tier-2, post-MVP)

| Phase | Effort | Deliverable |
|---|---|---|
| 1 — Schema migration | 30 min | ALTER loads (11 cols), CREATE carriers, CREATE offers, all via `/twin/sql` |
| 2 — Re-seed loads | 1 hr | Update `data/twin_seed_loads.sql` with max_buy, contacts, hazmat flags. Re-import. |
| 3 — Bridge endpoints | 3-4 hr | FastAPI implements `GET /api/v1/loads`, `GET /api/v1/loads/{id}`, `GET /api/v1/carriers/find`, `POST /api/v1/offers/log`. Bridge-shaped responses. |
| 4 — FMCSA integration | 2 hr | Get `FMCSA_WEB_KEY` from QCMobile portal. FastAPI proxies + caches FMCSA. Swap HR `verify_carrier` webhook URL to our endpoint. |
| 5 — Voice agent rewire | 1 hr | Update Read-from-Twin filters in `find_available_loads` and `search_loads_by_lane` to also surface max_buy, is_hazmat, etc. through the @ picker so Prompt can use them. |
| 6 — negotiate_evaluate v2 | 2-3 hr | Use load-level max_buy instead of computed % when present. Optional: query carriers + offers history mid-call for personalization (Tier-3 personas). |
| 7 — Dashboard enrichment | 1-2 hr | Surface max_buy savings, hazmat distribution, team-required percentage, branch attribution in dashboard views. |
| **Total** | **10-12 hr** | full Bridge API alignment + FMCSA caching + history-driven negotiation prep |

## Rejected alternatives

- **Skip Bridge API entirely** — would forfeit the "drop-in TMS replacement" narrative. Acceptable for MVP demo, weak for the broker-doc story.
- **Adopt Bridge API for MVP (refactor everything now)** — destabilizes the workflow we just published to dev. ~10-12 hr distracts from demo.
- **Adopt Bridge API but skip the carriers + offers tables** — half-measure. Without the storage, the endpoints have nothing to serve.
- **Use HR's `POST /api/v1/loads` upsert API to push our seed loads to HR** — backwards. We're the broker; HR shouldn't store our loads. Bridge expects HR's voice agent to READ from us via `GET /loads`.
- **Always proxy FMCSA without caching** — cheaper on dev work but expensive on calls. 24h cache is a one-time implementation that pays dividends forever.

## References

- Bridge API spec (Andres pasted 2026-04-25): `GET /api/v1/loads`, `GET /api/v1/loads/{id}`, `GET /api/v1/carriers/find`, `POST /api/v1/offers/log`, `POST /api/v1/loads` (load_upsert), `POST /api/v1/carriers` (carrier_upsert)
- [api-reference.md](../references/happyrobot/api-reference.md) — our project-scoped subset of HR Platform V2 API
- [iac-bundle.md](../references/happyrobot/iac-bundle.md) — IaC identifiers + state
- [ADR-002](ADR-002-iac-rebuild-from-zero.md) — companion Tier-2 work; Bridge API alignment can land on the same `iac` branch
- FMCSA QCMobile portal: https://safer.fmcsa.dot.gov/data-source.aspx — register for `FMCSA_WEB_KEY`
- HR demo FMCSA endpoint (currently used): `https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}?webKey=cdc33e44d693a3a58451898d4ec9df862c65b954`

## Consequences

- **Loads table grows from 15 → 25 columns** + 1 new index. Existing 25 seed rows backfill with NULLs for new fields; re-seed script populates them.
- **Two new Twin tables**: `carriers` (carrier registry + FMCSA cache), `offers` (negotiation event log). +6 indexes total.
- **FastAPI grows from 4 dashboard endpoints to 4 dashboard + 4 Bridge endpoints + 1 calls/log shim** = 9 endpoints.
- **FMCSA dependency moves from "HR demo" to "our own keyed proxy"** — production-grade. Requires `FMCSA_WEB_KEY` Fly secret.
- **Spec compliance preserved** — "API in a file or DB" still satisfied; we just speak the industry-standard dialect.
- **Architectural inversion noted in broker-doc**: "MVP ships HR-Twin-native (Read-from-Twin); Tier-2 adds Bridge-API parity for any future TMS swap-in." Demonstrates dual-mode mastery.
- **Migration cost when a real broker integrates**: ~zero. Their TMS pushes to our `POST /api/v1/loads` upsert (which we'd need to add as a Tier-3 endpoint), our search endpoints already speak Bridge dialect.
- **Open Tier-3 questions** documented but not solved here:
  - Multi-stop loads (`stops` JSONB) — defer until first multi-stop customer arrives
  - Hazmat granularity (`un_number`, `package_group`, `hazmat_class`) — defer until first hazmat-shipping broker
  - `team`/`branch` org hierarchy — defer until multi-broker SaaS
