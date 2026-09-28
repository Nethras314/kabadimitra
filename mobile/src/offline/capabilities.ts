// Explicit classification of what works offline vs what requires connectivity.
//
// We do NOT pretend the whole backend is offline-capable. Capture and local
// reads work offline; anything that depends on server state (AI, matching,
// quotes, verification, live aggregation) requires connectivity.

export type OfflineCapability = 'OFFLINE_SUPPORTED' | 'ONLINE_REQUIRED';

export const CAPABILITIES: Record<string, OfflineCapability> = {
  create_lot: 'OFFLINE_SUPPORTED',
  add_item: 'OFFLINE_SUPPORTED',
  attach_image_metadata: 'OFFLINE_SUPPORTED',
  record_weight: 'OFFLINE_SUPPORTED', // only when the parent transaction already exists
  record_payment: 'OFFLINE_SUPPORTED', // only when the parent transaction already exists
  view_cached_materials: 'OFFLINE_SUPPORTED',
  view_cached_prices: 'OFFLINE_SUPPORTED',
  view_safety_content: 'OFFLINE_SUPPORTED',

  ai_classify: 'ONLINE_REQUIRED',
  confirm_quote: 'ONLINE_REQUIRED',
  generate_matches: 'ONLINE_REQUIRED',
  nearby_recyclers: 'ONLINE_REQUIRED',
  live_price_estimate: 'ONLINE_REQUIRED',
  verify_recycler: 'ONLINE_REQUIRED',
};

export function isOfflineSupported(capability: string): boolean {
  return CAPABILITIES[capability] === 'OFFLINE_SUPPORTED';
}
