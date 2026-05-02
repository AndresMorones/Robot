# Carrier Eligibility — 7 Decline Reasons

> Internal reference for the inbound carrier voice agent's eligibility AND-gate.
> Each decline reason maps to one outcome tag captured in `calls_log` and
> classified by the post-call AI Classify Outcome node.

## Important framing

**These are OUR business rules, not FMCSA mandates.** FMCSA defines the data fields and the regulatory framework; the decision "decline a carrier when field X has value Y" is our internal eligibility policy informed by industry broker practice. The sources at the bottom verify what the FMCSA fields *mean*; they do not say "you must decline a carrier if `statusCode = I`." That part is on us.

## The 7 decline reasons (our AND-gate)

| # | Tag | FMCSA field | Trigger | Why we decline |
|---|---|---|---|---|
| 1 | `MC_NOT_FOUND` | `content` | `content` is `null` | MC not in FMCSA registry — typo, never issued, or purged. We can't verify any safety/authority data, so we can't tender. |
| 2 | `NOT_AUTHORIZED` | `allowedToOperate` | `allowedToOperate` ≠ `"Y"` | No active operating authority for interstate for-hire transportation. SAFER displays this as "NOT AUTHORIZED." |
| 3 | `INACTIVE_REVOKED` | `statusCode` | `statusCode` ∈ {`"I"`, `"R"`} | Authority is inactive (`I`) or revoked (`R`). Carrier cannot lawfully accept a tendered load while in this state. |
| 4 | `OUT_OF_SERVICE` | `oosDate` | `oosDate` is non-null | An FMCSA out-of-service order is currently in effect. Carrier cannot return to service until violations are corrected. |
| 5 | `UNSAFE_RATING` | `safetyRating` | `safetyRating` == `"Unsatisfactory"` | Carrier failed an FMCSA compliance review. Tendering exposes the broker to vicarious-negligence risk. |
| 6 | `LIKELY_BROKER` | `brokerAuthorityStatus` | `brokerAuthorityStatus` == `"A"` | Entity is registered as a property broker, not a motor carrier. Tendering to a broker is the textbook double-brokering pattern. |
| 7 | `NOT_A_CARRIER` | `censusTypeId` | `censusTypeId` ≠ `"C"` | MCMIS census classification indicates the entity is not a motor carrier (could be broker, shipper, freight forwarder, intermodal equipment provider). |

`safetyRating` of `null`, `"Conditional"`, or `"Satisfactory"` all PASS check 5 — only the literal string `"Unsatisfactory"` triggers a decline.

## Source endpoint

Our agent's `verify_carrier` tool calls the FMCSA SAFER QCMobile demo endpoint:

```
GET https://mobile.fmcsa.dot.gov/qc/services/carriers/{mc_number}?webKey={webKey}
```

Response is JSON. A successful lookup returns a `content` object containing the seven fields above. A miss returns `{"content": null}`.

## Verified sources (what FMCSA actually documents)

These links verify that the fields exist and what FMCSA's terminology means. **None of them state our decline policy** — they document the underlying data only.

- [FMCSA QCMobile API — Getting Started](https://mobile.fmcsa.dot.gov/QCDevsite/docs/getStarted) — endpoint base URL, webKey, JSON response format.
- [FMCSA QCMobile API — Carrier Lookup Endpoints](https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi) — endpoint reference for `/qc/services/carriers/{mc_number}`.
- [FMCSA QCMobile API — API Elements Description](https://mobile.fmcsa.dot.gov/QCDevsite/docs/apiElements) — official definitions for `allowToOperate`, `outOfService`, `outOfServiceDate`, `dotNumber`, `mcNumber`, `legalName`. Note: not every field the endpoint returns is documented here.
- [FMCSA SAFER Company Snapshot](https://safer.fmcsa.dot.gov/CompanySnapshot.aspx) — public UI for the same underlying data; useful for human verification.
- [FMCSA FAQ — Why is my operating authority shown as NOT AUTHORIZED on SAFER?](https://www.fmcsa.dot.gov/faq/why-my-operating-authority-status-shown-not-authorized-safety-and-fitness-electronic-records) — explains the NOT_AUTHORIZED state.
- [49 CFR Part 385 — Safety Fitness Procedures](https://www.ecfr.gov/current/title-49/subtitle-B/chapter-III/subchapter-B/part-385) — establishes the Satisfactory / Conditional / Unsatisfactory rating framework.
- [49 CFR § 371.2 — Broker definitions](https://www.law.cornell.edu/cfr/text/49/371.2) — defines what makes an entity a "broker" vs a "motor carrier."

## What FMCSA does NOT publicly document at field level

We could not find authoritative public documentation for:

- `statusCode` value table (`A` / `I` / `R`) — codes inferred from SAFER's "Operating Status" UI display values.
- `brokerAuthorityStatus` value `"A"` — not separately documented as an API element.
- `censusTypeId` value table (typically `C` = Carrier, `B` = Broker, `S` = Shipper, `F` = Freight Forwarder) — closest published reference is the [MCMIS Catalog: Census File Data Element Definitions](https://www.fmcsa.dot.gov/registration/mcmis-catalog-census-file-data-element-definitions), but it does not enumerate the value codes themselves.

These fields are present in the SAFER QCMobile JSON response in practice; their semantic interpretation is industry-inferred.

## Tier-2 production hardening (out of scope for this take-home)

- Replace shared demo `webKey` with a provisioned FMCSA developer credential.
- Add insurance verification (`/carriers/{dotNumber}/insurance`) to confirm BIPD coverage minimums per 49 CFR § 387.7.
- Integrate continuous carrier monitoring (Highway, Carrier411, RMIS, or equivalent) for between-call eligibility re-checks.
- Cache eligibility results for ~24h to absorb FMCSA latency and avoid duplicate calls during the same shift.
