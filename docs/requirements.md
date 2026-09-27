# Requirements

> Phase 0 document. Captures the approved requirements. Each requirement has a
> stable ID referenced by
> [requirement-traceability-matrix.md](requirement-traceability-matrix.md).

## 1. Users & roles

- **FR-USER-01** — Support six primary roles: Picker/Waste Collector, Kabadiwala,
  Aggregator, Recycler, Dismantler, Platform Admin.
- **FR-USER-02** — Provide role-based access control (RBAC) with
  organization-level data isolation.
- **FR-USER-03** — Allow a user to hold one or more roles via user-role mapping.

## 2. Localization

- **FR-I18N-01** — Support eight languages: Hindi, English, Marathi, Tamil,
  Telugu, Malayalam, Kannada, Bengali.
- **FR-I18N-02** — Localize collector-facing labels and taxonomy independently of
  the backend industrial taxonomy.

## 3. Collector UX & taxonomy

- **FR-UX-01** — Do not expose collectors to the complex industrial taxonomy.
- **FR-UX-02** — Collector-facing categories are: TV/Monitor, Computer/Laptop,
  Mobile/Electronics, PCB/Board, Cable/Wire, Battery, Motor, Magnet, Plastic,
  Metal, Lamp, Printer, Other, "I don't know".
- **FR-UX-03** — Represent equipment and recovered material **separately**.

## 4. Classification & AI

- **FR-AI-01** — AI suggests material category and subcategory.
- **FR-AI-02** — AI estimates classification confidence.
- **FR-AI-03** — AI detects supported visual material types.
- **FR-AI-04** — AI assists valuation.
- **FR-AI-05** — AI detects image quality issues.
- **FR-AI-06** — High confidence: AI suggestion -> collector confirms.
- **FR-AI-07** — Low confidence: collector manually selects or "I don't know".
- **FR-AI-08** — Escalation path when necessary: recycler review -> admin review.
- **FR-AI-09** — Collector corrections stored as feedback/training candidates,
  not automatically ground truth.
- **FR-AI-10** — AI must NOT claim exact gold/silver/copper content, chemical
  composition, certified hazardousness, or lab-grade material grade from an
  ordinary photograph.

## 5. Price discovery

- **FR-PRICE-01** — Do not create a single hard-coded price per material.
- **FR-PRICE-02** — Price is contextual: material, grade, location, date/time,
  buyer, weight, transport, source, verification.
- **FR-PRICE-03** — Every price observation carries provenance.
- **FR-PRICE-04** — Collector-entered buyer prices are observations, not
  authoritative market prices.

## 6. Recycler verification

- **FR-VERIF-01** — A recycler is not automatically "verified".
- **FR-VERIF-02** — Store: organization identity, facility, authorization number,
  issuing authority, authorization type, issue date, expiry date, verification
  source, verification date, accepted materials, service area, status.
- **FR-VERIF-03** — Statuses: Verified, Pending, Expiring, Expired, Suspended.
- **FR-VERIF-04** — Expired authorization excludes the recycler from matching.

## 7. Matching

- **FR-MATCH-01** — Match on: authorization, material acceptance, service area,
  distance, pickup availability, transport cost, expected net earnings, quote,
  reliability/history.
- **FR-MATCH-02** — Do not rank recyclers by gross price alone.

## 8. Transactions & weight

- **FR-TXN-01** — Lifecycle: `LOT_CREATED -> CLASSIFIED -> QUOTED ->
  QUOTE_ACCEPTED -> PICKUP_OR_DELIVERY -> WEIGHT_VERIFIED -> HANDOVER_CONFIRMED
  -> PAYMENT_RECORDED -> COMPLETED`.
- **FR-TXN-02** — Important state transitions create audit events.
- **FR-WEIGHT-01** — Support declared weight, pickup weight, and final/recycler
  accepted weight.

## 9. Payment

- **FR-PAY-01** — Support Cash, UPI, and Bank transfer.
- **FR-PAY-02** — Digital payment is not mandatory.

## 10. Offline-first sync

- **FR-SYNC-01** — SQLite is the local working database.
- **FR-SYNC-02** — Offline support: material capture, lot creation, weight entry,
  cached price info, safety content, draft transactions, payment recording
  (where appropriate).
- **FR-SYNC-03** — Backend remains authoritative.
- **FR-SYNC-04** — Use idempotency keys (e.g. `KC-LOT-260926-000482`) so repeated
  sync requests never create duplicate lots/transactions.

## 11. Media

- **FR-MEDIA-01** — Do not store large images in PostgreSQL.
- **FR-MEDIA-02** — Flow: Collector -> Cloudinary -> public ID/secure URL ->
  PostgreSQL metadata.

## 12. Geospatial

- **FR-GEO-01** — Use PostGIS.
- **FR-GEO-02** — Store recycler facility location as `GEOGRAPHY(Point, 4326)`.
- **FR-GEO-03** — Support nearby recycler search, service radius, distance
  calculation, and location-based matching.

## 13. Security

- **FR-SEC-01** — HTTPS everywhere.
- **FR-SEC-02** — Authentication and authorization.
- **FR-SEC-03** — Role-based access and organization-level isolation.
- **FR-SEC-04** — Input validation.
- **FR-SEC-05** — Rate limiting where appropriate.
- **FR-SEC-06** — Audit logging.
- **FR-SEC-07** — Secure image handling.
- **FR-SEC-08** — Secrets via environment variables; no hard-coded secrets.
- **FR-SEC-09** — Data minimization.
- **FR-SEC-10** — Do not collect Aadhaar in the MVP unless explicitly required
  later.

## 14. Non-functional

- **NFR-01** — Android-first mobile experience.
- **NFR-02** — Backend-authoritative business logic.
- **NFR-03** — AI is assistive, not authoritative.
- **NFR-04** — Reuse existing code; maintain backward compatibility; work
  incrementally.
- **NFR-05** — Documented decisions via the decision log.
