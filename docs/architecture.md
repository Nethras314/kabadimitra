# Architecture

> Phase 0 document. Represents the **approved** system architecture. Items not
> yet implemented are marked with their target phase.

## 1. System overview

Kabadi Mitra is a collector-first digital bridge between informal e-waste
collection and authorized recyclers. It is an **offline-first** mobile
application backed by an **authoritative** backend, with a web dashboard for
operational and administrative roles.

### Guiding constraints

- Backend-authoritative business logic.
- AI is **assistive**, not authoritative; uncertain classifications require
  human confirmation.
- Collector UX hides the industrial taxonomy behind simple categories.
- No single hard-coded prices; price is contextual and must carry provenance.
- Recyclers are never auto-verified; authorization status gates matching.
- No large media in PostgreSQL; images live in Cloudinary.
- Offline capture works locally (SQLite) and syncs with idempotency keys.

## 2. Components

| Component | Technology | Responsibility |
| --------- | ---------- | -------------- |
| Mobile | React Native + Expo + TypeScript + SQLite | Collector-facing capture, lots, offline-first sync |
| Backend | FastAPI + Python (REST) | Authoritative business logic, auth, matching, pricing, sync |
| Database | Supabase PostgreSQL + PostGIS | Relational core + geospatial |
| Media | Cloudinary | Image upload, transformation, secure URLs |
| Cache/jobs | Redis | Caching, background/async jobs |
| Web | Next.js + TypeScript | Admin/recycler/aggregator dashboards, maps |
| Maps | OpenStreetMap + MapLibre | Tiles, geocoding, distance |
| AI | Pluggable classification service | Suggestive category/subcategory, confidence, quality flags |

## 3. Deployment topology

```
[Collector]  Mobile (Expo/RN) --HTTPS--> FastAPI (Render)
                                         |-- Supabase PostgreSQL/PostGIS
                                         |-- Cloudinary (media)
                                         |-- Redis (cache/jobs)
                                         |-- AI service (pluggable)
[Admin/Recycler]  Web (Next.js/Vercel) --HTTPS--> FastAPI
```

## 4. Primary workflow

```
Collector
 -> Material Capture          (photo + simple category)
 -> Classification            (AI suggestion + collector confirmation)
 -> Digital Lot               (group items into a lot)
 -> Weight                    (declared -> pickup -> final)
 -> Price Discovery           (contextual, provenance-backed)
 -> Existing Buyer Comparison
 -> Verified Recycler Matching
 -> Recycler Quote
 -> Pickup/Delivery
 -> Final Weight
 -> Digital Handover
 -> Payment
 -> Earnings History
 -> Traceability
```

## 5. Domain model

Equipment and recovered material are represented **separately** (e.g. a monitor
is equipment; the PCB extracted from it is recovered material).

### Core entities

- Identity & org: `organizations`, `users`, `roles`, `user_roles`, `collectors`
- Recycler side: `recycler_organizations`, `recycler_facilities`,
  `recycler_authorizations`, `recycler_material_acceptance`,
  `recycler_service_areas`
- Taxonomy: `material_categories`, `material_subcategories`, `material_grades`,
  `material_conditions`, `material_hazards`
- Lots: `lots`, `lot_items`, `material_images`
- Pricing: `price_observations`, `price_history`, `recycler_quotes`
- Matching: `matches`
- Transactions: `transactions`, `transaction_events`, `weights`,
  `handover_records`
- Payments: `payments`, `payment_confirmations`
- Disputes: `disputes`, `dispute_events`
- AI: `ai_models`, `ai_decisions`, `ai_corrections`
- Ops: `audit_events`, `notifications`, `sync_operations`

The canonical schema is designed and implemented in **Phase 1**
([database-design.md](database-design.md) — TODO). This list is the approved
entity inventory, not the final DDL.

## 6. Key subsystems

### 6.1 Classification & AI

```
Photo -> AI prediction -> confidence -> collector confirmation
```

- **High confidence**: AI suggestion -> collector confirms.
- **Low confidence**: AI suggestion -> collector manually selects OR "I don't know".
- Escalation when necessary: recycler review -> admin review.
- Collector corrections are stored as **feedback/training candidates**, never
  automatically treated as ground truth.

AI must **not** claim from an ordinary photograph: exact gold/silver/copper
content, chemical composition, certified hazardousness, or lab-grade material
grade.

See [ai-architecture.md](ai-architecture.md) (TODO, Phase 3).

### 6.2 Price discovery

Price is contextual. No single hard-coded rate. Model inputs include: material,
grade, location, date/time, buyer, weight, transport, source, verification.
Price observations carry provenance; collector-entered buyer prices are
observations, not authoritative market prices. See [pricing-engine.md](pricing-engine.md)
(TODO, Phase 4).

### 6.3 Recycler verification

A recycler becomes "Verified" only through explicit, stored authorization data:
organization identity, facility, authorization number, issuing authority,
authorization type, issue/expiry dates, verification source/date, accepted
materials, service area, status. Statuses: `Verified`, `Pending`, `Expiring`,
`Expired`, `Suspended`. Expired authorization excludes the recycler from
matching. See [recycler-verification.md](recycler-verification.md) (TODO, Phase 4).

### 6.4 Matching

Matching ranks on: authorization, material acceptance, service area, distance,
pickup availability, transport cost, expected net earnings, quote,
reliability/history. It does **not** rank by gross price alone.

### 6.5 Transaction lifecycle

```
LOT_CREATED -> CLASSIFIED -> QUOTED -> QUOTE_ACCEPTED
  -> PICKUP_OR_DELIVERY -> WEIGHT_VERIFIED -> HANDOVER_CONFIRMED
  -> PAYMENT_RECORDED -> COMPLETED
```

Important state transitions create audit events.

### 6.6 Offline-first sync

SQLite is the local working database. Offline capabilities: material capture,
lot creation, weight entry, cached price info, safety content, draft
transactions, payment recording where appropriate. The backend remains
authoritative; sync uses idempotency keys (e.g. `KC-LOT-260926-000482`) so
repeated requests never create duplicate lots/transactions. See
[offline-sync.md](offline-sync.md) (TODO, Phase 6).

### 6.7 Geospatial

PostGIS. Recycler facilities store `GEOGRAPHY(Point, 4326)`. Supports nearby
recycler search, service radius, distance calculation, location-based matching.

## 7. Security

HTTPS, authentication, authorization, role-based access, organization-level
isolation, input validation, rate limiting, audit logging, secure image
handling, environment-variable secrets (no hard-coded secrets), and data
minimization. **Aadhaar is not collected in the MVP.** See
[security.md](security.md) (TODO, Phase 9).

## 8. Open questions / needs validation

- Exact AI provider(s) and self-hosted option — pluggable interface assumed.
- Field pilot logistics and sample-size targets (see field-pilot.md TODO).
- Whether Redis jobs run on Render or a separate worker host.
