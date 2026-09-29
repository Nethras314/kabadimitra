# Kabadi Mitra — System Overview

> This document is the entry point for the engineering documentation package.
> It summarizes the product, the architecture, and — critically — the **as-built
> state** of the repository, cross-referenced to the detailed documents that
> follow.

## 1. What Kabadi Mitra is

Kabadi Mitra is a **collector-first** digital bridge between informal e-waste
collection and authorized recyclers. It turns a collector's physical pickup into
a **traceable, price-transparent, and verifiable transaction** — from material
capture through payment and earnings history.

The primary users are the informal collectors (pickers / *kabadiwalas*). The
system lowers the barrier between them and authorized recyclers while keeping the
**backend authoritative** and **AI strictly assistive** (never a substitute for
human confirmation on uncertain classifications).

## 2. Core principles

| # | Principle |
| - | --------- |
| 1 | Backend-authoritative business logic; clients are never the source of truth. |
| 2 | AI is assistive, never authoritative; uncertain classifications require human confirmation. |
| 3 | Collector UX hides the industrial taxonomy behind 14 simple categories. |
| 4 | No single hard-coded price — price is contextual and provenance-backed. |
| 5 | Recyclers are never auto-verified; authorization status gates matching. |
| 6 | No large media in PostgreSQL; images live in Cloudinary. |
| 7 | Offline capture works locally (SQLite) and syncs with idempotency keys. |
| 8 | No Aadhaar in the MVP; data minimization by default. |

## 3. Architecture at a glance (approved topology)

```
React Native + Expo
        │
        ▼
      SQLite (offline working DB)
        │  (idempotent batch sync)
        ▼
     FastAPI  ──►  Supabase PostgreSQL + PostGIS
        │
        ├── Cloudinary   (media, signed upload)
        ├── Redis        (cache / jobs — reserved, not yet wired)
        └── AI Service   (pluggable classifier — assistive)

Next.js  ──►  Vercel  ──►  FastAPI
```

| Layer | Technology | Responsibility | Hosting |
| ----- | ---------- | -------------- | ------- |
| Mobile | React Native + Expo + TypeScript + SQLite | Collector capture, lots, offline-first sync | — |
| Backend | FastAPI + Python (REST) | Authoritative logic, auth, matching, pricing, sync | Render |
| Database | Supabase PostgreSQL + PostGIS | Relational core + geospatial | Supabase |
| Media | Cloudinary | Image upload, transformation, secure URLs | Cloudinary |
| Cache/jobs | Redis | Caching, background jobs (reserved) | — |
| Web | Next.js + TypeScript | Admin/recycler/aggregator dashboards, maps | Vercel |
| Maps | OpenStreetMap + MapLibre | Tiles, geocoding, distance | — |
| AI | Pluggable classification service | Suggestive category/subcategory, confidence | — |

## 4. Primary workflow

```
Collector → Material Capture → Classification → Digital Lot → Weight
  → Price Discovery → Existing Buyer Comparison → Verified Recycler Matching
  → Recycler Quote → Pickup/Delivery → Final Weight → Digital Handover
  → Payment → Earnings History → Traceability
```

## 5. Users

1. Picker / Waste Collector
2. Kabadiwala
3. Aggregator
4. Recycler
5. Dismantler
6. Platform Admin (plus support / operations / data-AI admin roles)

## 6. Languages

Hindi, English, Marathi, Tamil, Telugu, Malayalam, Kannada, Bengali (8).

## 7. Repository layout

```
kabadimitra/
├── .env.example         # env template (no secrets)
├── README.md            # ⚠ status banner is stale ("Phase 0")
├── render.yaml          # Render blueprint (FastAPI)
├── backend/             # FastAPI (13 routers, 32 endpoints) + migrations (19) + tests
├── mobile/              # Expo SDK 52 — offline data layer only (no screens)
├── web/                 # Next.js 14 — single "Nearby Recyclers" map page
└── docs/                # this documentation package
```

## 8. As-built status summary (verified 2026-09-28)

The repository is **mid-refactor** in the backend. Two structures coexist:

- **Mounted (live) backend** — `app/main.py` + `app/routers/*`: 13 routers, 32
  endpoints, inline hand-written SQL, the **legacy 6-role model**
  (`picker`, `kabadiwala`, `aggregator`, `recycler`, `dismantler`,
  `platform_admin`). This is what `run.py` serves.
- **Layered (unmounted) backend** — `app/foundation.py` +
  `app/{api,services,models,repositories,core}`: the route→service→repository
  target architecture, the **9-role model** with a hierarchy, and the
  0016–0019 schema. It is implemented and unit-tested (72 tests) but **only the
  health domain is mounted** in `foundation.py`; the full app is not yet served
  from it.

Status labels used throughout this package:

| Label | Meaning |
| ----- | ------- |
| **IMPLEMENTED** | Code exists and is verified by a passing test or build. |
| **PARTIAL** | Some behavior works; some is missing or unwired. |
| **PLANNED** | Designed/captured, not built. |
| **FUTURE** | Explicitly deferred. |
| **NEEDS FIELD VALIDATION** | Built but unverified against a real device/credential/model/database. |

## 9. Document map

| # | Document | Contents |
| - | -------- | -------- |
| 01 | System Overview | this document |
| 02 | Requirements | BR / UR / FR / TR hierarchy |
| 03 | Requirement Traceability Matrix | FR→API/DB/UI/TC/AT/evidence/status |
| 04 | System Architecture | approved + as-built architecture, gap analysis |
| 05 | Database Design | PostgreSQL + PostGIS schema (41 tables, 19 migrations) |
| 06 | API Design | REST endpoints, conventions, error model |
| 07 | Mobile Architecture | Expo/RN data layer, offline sync |
| 08 | Offline Sync | SQLite + idempotent batch sync contract |
| 09 | AI Architecture | assistive classifier, confidence tiers, corrections |
| 10 | Pricing Engine | contextual, provenance-backed pricing |
| 11 | Recycler Verification | explicit, expiry-aware authorization |
| 12 | Transaction Traceability | state machine, audit, earnings |
| 13 | Security | auth/RBAC/isolation/audit/rate-limiting |
| 14 | Testing Strategy | what is tested, what is blocked |
| 15 | Deployment | Render/Vercel/Supabase/Cloudinary topology |
| 16 | Field Pilot | validation plan (placeholders) |
| 17 | Dataset Strategy | training-data collection from corrections/observations |
| 18 | Decision Log | Architecture Decision Records (ADRs) |
| — | FINAL_STATUS | consolidated readiness + demo checklist |
