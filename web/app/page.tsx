'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

import { fetchNearby, NearbyRecycler } from '@/api/client';

// Map renders client-side only (needs a browser / DOM).
const NearbyMap = dynamic(() => import('@/components/NearbyMap'), { ssr: false });

export default function Home() {
  const [lat, setLat] = useState('19.0760');
  const [lng, setLng] = useState('72.8777');
  const [radius, setRadius] = useState('50');
  const [recyclers, setRecyclers] = useState<NearbyRecycler[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load(latitude: number, longitude: number, radiusKm: number) {
    try {
      setError(null);
      const results = await fetchNearby(latitude, longitude, radiusKm);
      setRecyclers(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRecyclers([]);
    }
  }

  useEffect(() => {
    load(parseFloat(lat), parseFloat(lng), parseFloat(radius));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Kabadi Mitra — Nearby Recyclers</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <label>Lat <input value={lat} onChange={(e) => setLat(e.target.value)} /></label>
        <label>Lng <input value={lng} onChange={(e) => setLng(e.target.value)} /></label>
        <label>Radius km <input value={radius} onChange={(e) => setRadius(e.target.value)} /></label>
        <button onClick={() => load(parseFloat(lat), parseFloat(lng), parseFloat(radius))}>
          Search
        </button>
      </div>

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <NearbyMap recyclers={recyclers} center={[parseFloat(lng), parseFloat(lat)]} />

      <ul>
        {recyclers.map((r) => (
          <li key={r.id}>
            {r.name} — {r.distance_km} km
          </li>
        ))}
      </ul>
      {recyclers.length === 0 && !error && <p>No recyclers found.</p>}
    </main>
  );
}
