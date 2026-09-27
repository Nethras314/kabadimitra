// Idempotency key generation for offline sync.
// Format: KC-<ENTITY>-<YYMMDD>-<6-digit sequence>, e.g. KC-LOT-260926-000482.

export function makeIdempotencyKey(entityType: string, date: Date, seq: number): string {
  const yy = String(date.getFullYear() % 100).padStart(2, '0');
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const seqStr = String(seq).padStart(6, '0');
  return `KC-${entityType.toUpperCase()}-${yy}${mm}${dd}-${seqStr}`;
}
