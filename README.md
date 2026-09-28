# Kabadi Mitra

A **collector-first** digital bridge between informal e-waste collection and
authorized recyclers. Kabadi Mitra turns a collector's physical pickup into a
traceable, price-transparent, and verifiable transaction — from material
capture through to payment and earnings history.

> Status: **Phase 0 — Foundation**. This repository currently contains the
> project foundation and documentation. Application code is implemented in
> later phases. See [docs/requirement-traceability-matrix.md](docs/requirement-traceability-matrix.md)
> for phase-by-phase status.

## Core principle

Informative collectors (pickers, *kabadiwalas*) are the primary users. The
system must lower the barrier between them and authorized recyclers while
keeping the **backend authoritative** and **AI assistive** (never a
substitute for human confirmation on uncertain classifications).

## Architecture at a glance

| Layer        | Technology                      | Hosting   |
| ------------ | ------------------------------- | --------- |
| Mobile       | React Native / Expo / TypeScript / SQLite | —    |
| Backend      | FastAPI / Python (REST)         | Render    |
| Database     | Supabase PostgreSQL + PostGIS    | Supabase  |
| Media        | Cloudinary                      | Cloudinary |
| Cache/jobs   | Redis                           | —         |
| Web          | Next.js / TypeScript            | Vercel    |
| Maps         | OpenStreetMap / MapLibre        | —         |
| AI           | Pluggable classification service (assistive) | — |

Full details: [docs/architecture.md](docs/architecture.md).

## Repository layout

```
kabadimitra/
├── .env.example         # Environment variable template (no secrets)
├── .gitignore
├── README.md
├── docs/                # Architecture, requirements, RTM, decision log
├── backend/             # FastAPI service (Phase 2+)
├── mobile/              # Expo / React Native app (Phase 7+)
└── web/                 # Next.js web app (Phase 8+)
```

## Primary users

1. Picker / Waste Collector
2. Kabadiwala
3. Aggregator
4. Recycler
5. Dismantler
6. Platform Admin

## Languages

Hindi, English, Marathi, Tamil, Telugu, Malayalam, Kannada, Bengali.

## Development phases

- **Phase 0 — Foundation** (current): scaffold, docs, decision log, env template.
- **Phase 1 — Database**: PostGIS schema + seed taxonomy.
- **Phase 2 — Backend core**: FastAPI, auth/RBAC, org isolation, audit events.
- **Phase 3 — Material capture + AI**: lots, items, images, Cloudinary, AI.
- **Phase 4 — Pricing + recycler verification**.
- **Phase 5 — Matching + transaction lifecycle**.
- **Phase 6 — Offline sync** (SQLite + idempotency).
- **Phase 7 — Mobile** (Expo/RN).
- **Phase 8 — Web** (Next.js) + geospatial/maps.
- **Phase 9 — Security hardening + deployment**.

## Quick start

Not yet applicable — application code ships in later phases. Once the backend
exists:

```bash
cp .env.example .env   # then fill in values
```

## Documentation

- [Architecture](docs/architecture.md)
- [Requirements](docs/requirements.md)
- [Requirement Traceability Matrix](docs/requirement-traceability-matrix.md)
- [Decision Log](docs/decision-log.md)

## License

TODO: choose and add a license.