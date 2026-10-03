import { Check, FolderOpen, ShieldCheck, X } from "lucide-react";
import type { RunSummary, TransferRecord } from "../types";
import { formatBytes, formatCount, formatDuration, formatStamp, titleCase } from "../lib/format";

export function HistoryPanel({ history }: { history: RunSummary[] }) {
  const recent = history.slice().reverse();

  return (
    <div className="history">
      {recent.length === 0 ? (
        <div className="empty-row">No completed runs recorded yet.</div>
      ) : (
        recent.map((run, index) => {
          const failed = run.errors > 0 || run.status.toLowerCase().includes("fail");
          return (
            <div className="history-row" key={run.runId || index}>
              <span className="history-icon" data-status={failed ? "failed" : "ok"}>
                {failed ? <X size={10} /> : <Check size={10} />}
              </span>
              <div className="history-main">
                <div className="history-title">{titleCase(run.status)}</div>
                <div className="history-meta">
                  {formatStamp(run.startedAt)} · {formatDuration(run.durationSeconds)}
                  {run.filesSkipped > 0 ? ` · ${formatCount(run.filesSkipped)} skipped` : ""}
                  {run.bytesTransferred > 0 ? ` · ${formatBytes(run.bytesTransferred)}` : ""}
                </div>
              </div>
              <span className="history-count tnum">{formatCount(run.filesPushed)} files</span>
            </div>
          );
        })
      )}
    </div>
  );
}

export function VerifiedPanel({ transfers, onReveal }: { transfers: TransferRecord[]; onReveal: () => void }) {
  const recent = transfers.slice(-40).reverse();

  return (
    <>
      <div className="verified">
        {recent.length === 0 ? (
          <div className="empty-row">Verified transfers appear here after the first relay.</div>
        ) : (
          recent.map((record, index) => (
            <div className="verified-row" key={`${record.at}-${index}`}>
              <ShieldCheck size={12} color="var(--success)" />
              <span className="verified-name">
                {record.file}
                {record.livePhoto ? " · live" : ""}
              </span>
              <span className="verified-size tnum">{formatBytes(record.sizeBytes)}</span>
            </div>
          ))
        )}
      </div>
      <div className="panel-foot">
        <span>Appended to runtime/transfers.jsonl</span>
        <button className="button button-ghost" onClick={onReveal}>
          <FolderOpen size={13} />
          Reveal
        </button>
      </div>
    </>
  );
}