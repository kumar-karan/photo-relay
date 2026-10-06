import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, CheckCircle2, Info, ListChecks, XCircle } from "lucide-react";
import type { RelayEvent } from "../types";
import { formatClock } from "../lib/format";

const GLYPH: Record<string, React.ReactNode> = {
  info: <Info size={11} />,
  success: <CheckCircle2 size={11} />,
  complete: <CheckCircle2 size={11} />,
  warning: <AlertTriangle size={11} />,
  error: <XCircle size={11} />,
};

/** Routine per-file chatter is noise in a milestone list. */
function isMilestone(event: RelayEvent): boolean {
  if (event.kind === "error" || event.kind === "warning" || event.kind === "complete") return true;
  if (!event.phase) return false;
  return ["starting", "connecting", "scanning", "done", "failed"].includes(event.phase);
}

/**
 * Milestone timeline.
 *
 * Feeds the relay produces one line per file, which turns a status panel into
 * a wall of console text. Only stage changes and problems are listed here;
 * per-file progress lives in the transfer stream instead.
 */
export function MilestoneFeed({ events }: { events: RelayEvent[] }) {
  const milestones = events.filter(isMilestone).slice(0, 40);

  return (
    <div className="milestones">
      <AnimatePresence initial={false} mode="popLayout">
        {milestones.length === 0 ? (
          <motion.div
            className="milestone-empty"
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="milestone-empty-icon">
              <ListChecks size={18} />
            </div>
            <strong>No milestones yet</strong>
            <span>Stage changes and problems appear here while a relay runs.</span>
          </motion.div>
        ) : (
          milestones.map((event, index) => (
            <motion.div
              className="milestone"
              key={`${event.at}-${index}`}
              data-kind={event.kind}
              layout
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
            >
              <span className="milestone-rail">
                <span className="milestone-dot" />
                {index < milestones.length - 1 && <span className="milestone-line" />}
              </span>
              <span className="milestone-glyph">{GLYPH[event.kind] ?? GLYPH.info}</span>
              <div className="milestone-body">
                <div className="milestone-message">{event.message}</div>
                {event.phase && <div className="milestone-phase">{event.phase}</div>}
              </div>
              <span className="milestone-time">{formatClock(event.at)}</span>
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  );
}