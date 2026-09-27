# Kabadi Mitra — Web (Next.js)

Admin/recycler dashboard. Phase 8 delivers a **nearby recycler** view backed by
the PostGIS endpoint and rendered on a MapLibre map (OpenStreetMap tiles, no API
key).

> **Status: Phase 8 scaffold.** The nearby-recycler list + map are implemented
> and the app builds; full auth wiring, dashboards, and interactive workflows
> are follow-up work.

## Run

```bash
cd web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

The backend `/api/v1/recycler/nearby` endpoint requires a Supabase JWT; pass a
token (via Supabase Auth) or the request returns 401.

## Structure

```
web/
├── app/
│   ├── layout.tsx         # root layout
│   └── page.tsx           # nearby-recycler page (client component)
├── src/
│   ├── api/client.ts      # backend fetch client
│   └── components/NearbyMap.tsx  # MapLibre + OSM map
└── next.config.js
```

## Notes

- Map uses OpenStreetMap raster tiles via MapLibre GL (no token, with attribution).
- The nearby search is backed by `GET /api/v1/recycler/nearby` (PostGIS
  `ST_DWithin`/`ST_Distance`), returning verified non-expired recyclers ordered
  by distance.
