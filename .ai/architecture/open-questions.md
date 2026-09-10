# Architecture — Open Questions

rev 2 (2026-09-09). Every question has a **default already applied** in the architecture documents,
so none of these blocks /plan or /build. Answering one may change a document; leaving one unanswered
changes nothing.

Ranked: **important** (worth a minute at GATE_5) then **nice-to-know**.

## Important

**OQ-12 — Confirm the Fly proxy peer set and hop count (promoted from nice-to-know in rev 2, SEC-F1).**
This was mis-ranked in rev 1: a wrong value does not degrade a nicety, it makes the rate-limit key
**attacker-chosen**, which silently voids threats #1, #23, #33 and #35. Default applied (ADR-020, rev 2):
the immediate peer address is authoritative; `Fly-Client-IP` and `X-Forwarded-For` are read **only**
when the peer is inside an explicitly configured `TRUSTED_PEER_CIDRS`, and are discarded otherwise;
`selfcheck` refuses to start if either that or `TRUSTED_PROXY_HOPS` is unset. What is still open is
purely factual and belongs to /release: **what are Fly's proxy source addresses as seen by the
machine, and does the header survive one hop or more?** Verified by the SEC-T21 test in CI and by a
live spoofing attempt at /release (infrastructure §13). Getting the values wrong now fails closed
(everything buckets on the peer), which is the safe direction.

**OQ-1 — Is the 45-minute idle session window right for the office?**
ADR-007 left the choice inside a 30–60 min range. Default applied: **45 min idle, 9 h absolute,
browser-close expiry**. Shorter means a clerk re-authenticates during a long phone call; longer
weakens the bound on a hijacked session. Changing it is an environment variable, not code.

**OQ-2 — Where should the encrypted monthly database dump be written?**
ADR-006 enabled it because the human holds the key, but the destination is still unnamed. Default
applied: **the dump does not run**; platform daily backups (~7 days, confirm at signup) are the only
mechanism, so the accepted data-loss window is up to a day and history beyond the platform's
retention does not exist off-platform. Naming a destination (with its own write-scoped credential
and a ~90-day lifecycle rule) turns it on at ~$0–1/mo. **Rev 2 (REL-F4/SEC-F15): go-live is not
gated on this, but the gap is now a named accepted residual rather than a claimed control** — every
copy of the citizen database lives with one vendor, and threat #28 is recorded as `accepted` for
exactly that reason (infrastructure §8). Answering this question is the single cheapest way to
retire an accepted risk in the whole model.

**OQ-3 — What is the registrable `.in` domain, and when is it attached?**
The cookie design requires the static site and the API to share one registrable domain, and the
domain must be live on both hosts **before any real citizen data is entered**. Default applied:
`www.<domain>.in` / `api.<domain>.in` placeholders throughout; `/plan` fills them in and /release
gates on it. If a single registrable domain turns out to be impossible, the answer is a BFF proxy
returning to GATE_2 — never `SameSite=None`.

**OQ-4 — Is the complaint-number shape acceptable to read aloud?**
Default applied: **8 random Crockford base32 symbols + 1 checksum symbol, displayed `XXXX-XXXXX`**
(e.g. `7K4M-QP2R9`), case-insensitive, with `I/L→1` and `O→0` accepted on input. Nine characters is
the shortest form that meets the ≥40-bit floor plus a checksum. A shorter number would weaken
ADR-008's anti-enumeration floor; a prefix like `PC-` can be added for recognisability at the cost
of two more characters to dictate.

**OQ-5 — Should a second admin clerk account be provisioned at go-live?**
BR-013 recommends it as the mitigation for admin self-lockout (Q-015); the UI shows a persistent
advisory when only one admin exists. Default applied: **not created automatically** — the office
decides. **Rev 2 (REL-F2) changes what "no second admin" costs.** Rev 1's break-glass did not
actually work: `bootstrap-admin` is a no-op once an admin exists and `unlock-account` never changes
a password, so a forgotten admin password had **no** recovery path. There is now a real one — the
operator CLI **`reset-admin-password <username>`** on a Fly shell, which issues an OTP by the same
code path as the in-app reset and writes a `security_event` (backend §12, runbook infrastructure
§12.1). So a second admin is now an **availability convenience** (recover in two minutes in-app
instead of waiting for the human with the Fly account), not the only way back in. Still worth
answering, but no longer load-bearing.

**OQ-6 — Does the residency rule reach the static assets?**
Default applied: **no** — the exported bundle contains no citizen data (A-T1a), so it stays on the
free Render CDN. If a state IT policy reads "all project infrastructure in India", serving `out/`
from a second Fly machine in `bom` costs +$2–5/mo and zero code change.

## Nice-to-know

**OQ-7 — Which uptime pinger, and which mailbox receives the alerts?**
Default applied: a free tier (UptimeRobot or Better Stack) hitting `/healthz` every 5 min, alerting a
**shared office address** rather than one person. An unread mailbox makes NFR-007's evidence trail
exist but unobserved.

**OQ-8 — TOTP for the admin clerk?**
Default applied: **not built**. No requirement asks for it, and it adds a lockout mode to an office
with one admin. Offered at +1 dependency and ~0.5–1 day if wanted (threat #6).

**OQ-9 — Should complaint *detail views* be audited, not just writes?**
Default applied: **no** — reconfirmed in rev 2 after SEC-F4 asked for a bounding control. All clerks
legitimately see all records (A1/FR-007), so a `complaint_viewed` row per open is noise nobody will
read at 1–5 clerks. What was added instead is a **ceiling**, not an audit trail: the `detail`
limiter scope at `RATE_LIMIT_DETAIL_PER_HOUR = 120` keyed on **`user_id`** — not per session, which
is what rev 2 said and rev 3 corrected (R3-2), because login mints sessions for free — covering every
route that returns name or phone, including `GET /api/complaints/{id}/activity`, plus a companion
`search` scope at 120/user/hour on `POST /api/complaints/search` (R4-2). Each produces a
`throttle_*` event only when someone is actually vacuuming. The residual — a patient hijacked
session exfiltrating the contact list over hours, at a bounded *rate* rather than a bounded total —
is recorded as **accepted** in threat #24 rather than claimed as mitigated. Answering "yes" here would tighten #24; it costs one event type
and some noise.

**OQ-10 — Platform log retention: what is it actually?**
Default applied: assume days, and treat `security_event` as the durable record. Confirm the figure
at signup and record it in /release; if it is very short, the case for a second durable sink gets
stronger.

**OQ-11 — Are the fixed public status messages final?**
Default applied: five enumerated messages, one per status, worded in `/ux`
(`interaction-patterns.md`), served as `public_update`. They are data in a single strings module, so
changing wording later is a one-file change with no schema impact — and the Telugu translation lands
in the same place (ADR-014 Q1).

**OQ-13 — Should the 7-day correction window and the 20/min lookup limit be tunable by the office?**
Default applied: both are environment variables (`EDIT_WINDOW_DAYS=7`,
`RATE_LIMIT_LOOKUP_PER_MIN=20`), changed by the human with a redeploy — not by a clerk in a settings
screen. A settings UI has no requirement and would need its own authorization story.

## Human answers at GATE_3+GATE_5 (2026-09-10)

- OQ-2: default confirmed — no dump destination for the test project; the monthly dump stays dormant, threat #28 stays accepted.
- OQ-3: placeholders for now; /plan keeps `www.<domain>.in` / `api.<domain>.in`; /release gates on the real domain.
- OQ-4: confirmed — `XXXX-XXXXX` Crockford base32 (ADR-016).
- OQ-1: confirmed — 45 min idle / 9 h absolute (ADR-019).
- OQ-5: **changed** — a second admin clerk account IS provisioned at go-live (the go-live checklist in /release adds it; `bootstrap-admin` creates the first, the first admin creates the second in-app).
