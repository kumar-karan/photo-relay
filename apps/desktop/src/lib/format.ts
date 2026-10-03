const UNITS = ["B", "KB", "MB", "GB", "TB"];

export function formatBytes(bytes: number | undefined | null, precision = 1): string {
  const value = Number(bytes ?? 0);
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const exponent = Math.min(Math.floor(Math.log(value) / Math.log(1000)), UNITS.length - 1);
  const scaled = value / Math.pow(1000, exponent);
  const digits = exponent === 0 ? 0 : scaled >= 100 ? 0 : precision;
  return `${scaled.toFixed(digits)} ${UNITS[exponent]}`;
}

export function formatRate(mbps: number | undefined | null): string {
  const value = Number(mbps ?? 0);
  if (!Number.isFinite(value) || value <= 0) return "—";
  return `${value.toFixed(1)} MB/s`;
}

export function formatCount(value: number | undefined | null): string {
  return Number(value ?? 0).toLocaleString();
}

/** Trim an engine timestamp down to a readable minute. */
export function formatClock(value: string | undefined | null): string {
  if (!value) return "—";
  const text = value.trim();
  const time = text.match(/(\d{2}:\d{2}:\d{2})/);
  if (time) return time[1];
  const parsed = new Date(text);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  return text;
}

export function formatStamp(value: string | undefined | null): string {
  if (!value) return "No captures yet";
  const parsed = new Date(value.includes("T") ? value : value.replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(seconds: number | undefined | null): string {
  const value = Number(seconds ?? 0);
  if (!Number.isFinite(value) || value <= 0) return "0s";
  if (value < 60) return `${value.toFixed(value < 10 ? 1 : 0)}s`;
  const minutes = Math.floor(value / 60);
  const rest = Math.round(value % 60);
  if (minutes < 60) return `${minutes}m ${rest.toString().padStart(2, "0")}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${(minutes % 60).toString().padStart(2, "0")}m`;
}

/** Estimated seconds remaining from measured throughput and remaining bytes. */
export function estimateEta(transferredBytes: number, totalBytes: number, rateMbps: number): number | null {
  if (!rateMbps || rateMbps <= 0 || !totalBytes || totalBytes <= 0) return null;
  const remaining = Math.max(totalBytes - transferredBytes, 0);
  if (remaining <= 0) return 0;
  return remaining / (rateMbps * 1_000_000);
}

export function percentOf(done: number, total: number): number {
  if (!total || total <= 0) return 0;
  return Math.min(100, Math.max(0, (done / total) * 100));
}

export function titleCase(value: string | undefined | null): string {
  if (!value) return "Idle";
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}