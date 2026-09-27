// Client-side UUID v4 generator (dependency-free, Math.random based).
// NOTE: for production prefer crypto.randomUUID() / expo-crypto; this is an MVP
// convenience that is safe for single-client offline ID assignment.

export function uuidv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
