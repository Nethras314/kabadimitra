// Backend API client. NEXT_PUBLIC_API_URL is injected at build time.

export interface NearbyRecycler {
  id: string;
  name: string;
  distance_km: number;
  latitude: number | null;
  longitude: number | null;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchNearby(
  lat: number,
  lng: number,
  radiusKm: number,
  token?: string,
): Promise<NearbyRecycler[]> {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_km: String(radiusKm),
  });
  const res = await fetch(`${BASE_URL}/api/v1/recycler/nearby?${params}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`nearby failed: ${res.status}`);
  return (await res.json()) as NearbyRecycler[];
}
