import { motion } from "motion/react";
import { Check, X } from "lucide-react";
import type { RunSummary } from "../types";
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
            <motion.div
              className="history-row"
              key={run.runId || index}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.24, delay: Math.min(index * 0.04, 0.3), ease: [0.22, 1, 0.36, 1] }}
            >
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
            </motion.div>
          );
        })
      )}
    </div>
  );
}