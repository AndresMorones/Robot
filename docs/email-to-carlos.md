# Email to Carlos Becker — Submission

**To:** c.becker@happyrobot.ai
**Cc:** [PLACEHOLDER — recruiter email]
**From:** Andres Morones <andres20021122@gmail.com>
**Subject:** Inbound Carrier Sales POC — submission

---

Hi Carlos,

Ahead of our meeting, here's my submission for the Inbound Carrier Sales take-home. The role energizes me and I wanted the build to reflect the kind of work I'd want to do alongside the HappyRobot team day-to-day.

The POC is a fully working inbound carrier voice agent on HappyRobot — FMCSA verification, Twin-backed load search, deterministic 3-round negotiation, mid-call booking, mocked sales-rep transfer, and full post-call analytics — paired with a custom Next.js 15 dashboard and a FastAPI backend. Both services are containerized and deployed on Fly.io behind HTTPS with shared Bearer auth on every `/v1/*` endpoint.

A few decisions worth flagging that shaped the build:

- **Negotiation policy isolated in an HR Run Python sidecar** under the `negotiate_rate` tool — the floor, max rounds, and urgency tiers live outside the main Prompt's context, so transcript-level prompt injection cannot extract or move them.
- **Two-table booking pattern** (ADR-005): bookings are persisted mid-call by a `book_load` tool fire so a hangup never costs us the booking, while `calls_log` is written post-call by AI Extract → Case Health Score. `UNIQUE(call_id, load_id)` provides idempotency at the schema layer.
- **Effective-delta KPI on the Economics tab**: avg loadboard rate vs avg agreed rate side-by-side, with the negotiated delta surfaced as the primary dollar number a brokerage director cares about.
- **28 languages enabled** + Contact Intelligence on, mostly to show what's possible without a code change once the platform is in place.

Links:

- Repo: [PLACEHOLDER — GitHub URL]
- API: https://robot-api-andres-morones.fly.dev
- Dashboard: https://robot-dashboard-andres-morones.fly.dev
- HR workflow (Production env share): [PLACEHOLDER — HR share URL]
- 5-min Loom demo: [PLACEHOLDER — Loom URL]
- Acme broker doc: `docs/broker-doc.md` in the repo (narrative + Tier-2/3 roadmap)
- Architecture decisions: `docs/decisions/ADR-005-two-table-booking-pattern.md` + `ADR-006-nextjs-dashboard-commit.md`
- Reproduce deployment: `docs/iac/reproduce.md`

Happy to walk through anything in more depth — I'm available on short notice for follow-ups. Thanks for the opportunity, looking forward to the conversation.

Best,
Andres Morones

---

## Subject-line alternatives

1. **Inbound Carrier Sales POC — submission** _(suggested default — direct, scannable in a busy inbox)_
2. **HappyRobot FDE take-home — Andres Morones submission**
3. **Carrier voice agent + dashboard — POC ready for review**

---

## Placeholders to fill before sending

- [ ] Recruiter email in Cc
- [ ] GitHub repo URL
- [ ] HR Production-env workflow share URL
- [ ] Loom video URL
