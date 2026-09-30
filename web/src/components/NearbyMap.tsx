'use client';

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// Shape returned by GET /api/v1/recycler/nearby (kept local so the map does not
// depend on the API client's surface).
export interface NearbyRecycler {
  id: string;
  name: string;
  distance_km: number;
  latitude: number | null;
  longitude: number | null;
}

// OpenStreetMap raster tiles — no API key required (attribution included).
const OSM_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
};

export default function NearbyMap({
  recyclers,
  center,
}: {
  recyclers: NearbyRecycler[];
  center: [number, number];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: OSM_STYLE,
      center,
      zoom: 10,
    });
    mapRef.current = map;

    for (const r of recyclers) {
      if (r.latitude != null && r.longitude != null) {
        new maplibregl.Marker()
          .setLngLat([r.longitude, r.latitude])
          .setPopup(new maplibregl.Popup().setText(`${r.name} (${r.distance_km} km)`))
          .addTo(map);
      }
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [recyclers, center]);

  return <div ref={containerRef} style={{ width: '100%', height: 400 }} />;
}
