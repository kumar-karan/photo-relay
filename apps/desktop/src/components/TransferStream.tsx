import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, Check, CircleAlert, Film, Image as ImageIcon, Layers, Loader } from "lucide-react";
import type { TransferRecord } from "../types";
import { formatBytes, formatClock } from "../lib/format";

type Props = {
  transfers: TransferRecord[];
  /** Cap the visible list so a long run cannot grow the DOM without bound. */
  limit?: number;
};

function KindIcon({ record }: { record: TransferRecord }) {
  if (!record.verified) return <Loader size={12} className="spin" />;
  if (record.error) return <AlertTriangle size={12} />;
  const name = record.file.toLowerCase();
  if (name.endsWith(".heic") || name.endsWith(".heif")) return <Layers size={12} />;
  if (name.endsWith(".mov") || name.endsWith(".mp4") || name.endsWith(".m4v")) return <Film size={12} />;
  return <ImageIcon size={12} />;
}

/**
 * Per-file transfer rows.
 *
 * The engine reports one line per file. Rendering those lines verbatim reads
 * like a console, so each confirmed file becomes an element instead: an icon
 * for its kind, the name, its size and the time it landed.
 */
export function TransferStream({ transfers, limit = 14 }: Props) {
  const recent = transfers.slice(-limit).reverse();

  return (
    <div className="stream">
      <AnimatePresence initial={false} mode="popLayout">
        {recent.length === 0 ? (
          <motion.div
            className="stream-empty"
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            Nothing transferred yet
          </motion.div>
        ) : (
          recent.map((record, index) => (
            <motion.div
              className="stream-row"
              key={`${record.at}-${index}`}
              layout
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              data-state={record.error ? "error" : record.verified ? "verified" : "pending"}
            >
              <span className="stream-icon">
                <KindIcon record={record} />
              </span>
              <div className="stream-body">
                <div className="stream-name" title={record.file}>
                  {record.file}
                </div>
                <div className="stream-meta">
                  {record.livePhoto && <span className="tag">Live Photo</span>}
                  {record.capturedAt && <span className="stream-captured">Captured {formatClock(record.capturedAt)}</span>}
                  {record.error && <span className="stream-error">{record.error}</span>}
                </div>
              </div>
              <span className="stream-size">{formatBytes(record.sizeBytes)}</span>
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  );
}