import { AnimatePresence, motion } from "motion/react";
import { Activity, AlertTriangle, CheckCircle2, Info, Sparkles, XCircle } from "lucide-react";
import type { RelayEvent } from "../types";
import { formatClock } from "../lib/format";

const GLYPH: Record<string, React.ReactNode> = {
  info: <Info size={10} />,
  success: <CheckCircle2 size={10} />,
  complete: <Sparkles size={10} />,
  warning: <AlertTriangle size={10} />,
  error: <XCircle size={10} />,
};

export function ActivityFeed({ events }: { events: RelayEvent[] }) {
  return (
    <div className="feed">
      <AnimatePresence initial={false}>
        {events.length === 0 ? (
          <div className="feed-empty">
            <div className="feed-empty-icon">
              <Activity size={17} />
            </div>
            <strong>Waiting for a relay</strong>
            <span>Connect both phones, run the device check, then start the relay.</span>
          </div>
        ) : (
          events.map((event, index) => (
            <motion.div
              className="event"
              key={`${event.at}-${index}`}
              data-kind={event.kind}
              layout="position"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              <span className="event-glyph">{GLYPH[event.kind] ?? GLYPH.info}</span>
              <div className="event-body">
                <div className="event-message">{event.message}</div>
                {event.file && event.capturedAt && (
                  <div className="event-file">captured {event.capturedAt}</div>
                )}
                {event.file && event.livePhoto && !event.capturedAt && <div className="event-file">live photo</div>}
              </div>
              <span className="event-time">{formatClock(event.at)}</span>
            </motion.div>
          ))
        )}
      </AnimatePresence>
    </div>
  );
}