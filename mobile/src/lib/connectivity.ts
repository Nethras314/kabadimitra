// Connectivity detection. The sync layer depends on this abstraction so tests
// can simulate airplane mode without touching the network.

export interface Connectivity {
  isOnline(): Promise<boolean>;
}

/** Fixed connectivity for tests and deterministic scenarios. */
export class StaticConnectivity implements Connectivity {
  private online: boolean;

  constructor(online = true) {
    this.online = online;
  }

  setOnline(online: boolean): void {
    this.online = online;
  }

  async isOnline(): Promise<boolean> {
    return this.online;
  }
}

/** Reachability check against the backend health endpoint (with timeout). */
export class ReachabilityConnectivity implements Connectivity {
  constructor(
    private readonly healthUrl: string,
    private readonly timeoutMs = 5000,
  ) {}

  async isOnline(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeoutMs);
      const res = await fetch(this.healthUrl, { method: 'GET', signal: controller.signal });
      clearTimeout(timer);
      return res.ok;
    } catch {
      return false;
    }
  }
}
