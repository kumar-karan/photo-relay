export type RelayPhase =
  | "idle"
  | "starting"
  | "connecting"
  | "preflight"
  | "scanning"
  | "downloading"
  | "converting"
  | "transferring"
  | "pushing"
  | "indexing"
  | "done"
  | "failed";

export type RelayEvent = {
  kind: "info" | "success" | "warning" | "error" | "complete";
  message: string;
  at: string;
  phase?: RelayPhase;
  file?: string;
  totalFiles?: number;
  completedFiles?: number;
  totalBytes?: number;
  transferredBytes?: number;
  rateMbps?: number;
  capturedAt?: string;
  livePhoto?: boolean;
  sizeMb?: number;
};

export type RunSummary = {
  runId: string;
  startedAt: string;
  finishedAt?: string;
  filesPushed: number;
  filesSkipped: number;
  errors: number;
  bytesTransferred: number;
  durationSeconds: number;
  newWatermark?: string;
  status: string;
};

export type TransferRecord = {
  at: string;
  file: string;
  sizeBytes: number;
  capturedAt?: string;
  livePhoto: boolean;
  verified: boolean;
  error?: string;
};

export type Dashboard = {
  running: boolean;
  engineFound: boolean;
  phase: RelayPhase;
  totalFiles: number;
  completedFiles: number;
  totalBytes: number;
  transferredBytes: number;
  rateMbps: number;
  elapsedSeconds: number;
  errors: number;
  currentFile: string;
  devices: Record<string, string>;
  status: string;
  totalSyncedFiles: number;
  lastSyncedTimestamp: string;
  history: RunSummary[];
  transfers: TransferRecord[];
  recentEvents: RelayEvent[];
  latestLog: string;
  projectRoot: string;
  engineVersion: string;
};