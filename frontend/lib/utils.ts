export function formatConfidence(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return `${Math.round(value * 100)}%`;
}

export function formatLatency(ms: number | null): string {
  if (ms === null) {
    return "—";
  }

  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }

  return `${Math.round(ms)}ms`;
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(4)}`;
}

export function relativeTime(isoString: string): string {
  const seconds = Math.max(
    0,
    Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  );

  if (seconds < 60) {
    return "just now";
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);
  return `${days} days ago`;
}

export function truncate(str: string, len: number): string {
  if (str.length <= len) {
    return str;
  }

  return `${str.slice(0, Math.max(0, len - 1))}…`;
}
