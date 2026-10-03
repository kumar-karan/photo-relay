import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, X } from "lucide-react";

export function StartDialog({ open, onCancel, onConfirm, busy }: { open: boolean; onCancel: () => void; onConfirm: () => void; busy: boolean }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={onCancel}
        >
          <motion.div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-label="Start the photo relay"
            initial={{ opacity: 0, y: 14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.99 }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            onClick={(event) => event.stopPropagation()}
          >
            <button className="dialog-close" onClick={onCancel} aria-label="Close">
              <X size={15} />
            </button>
            <div className="dialog-icon">
              <ArrowRight size={17} />
            </div>
            <h2 className="dialog-title">Start the photo relay?</h2>
            <p className="dialog-copy">
              Photo Relay will pull new media from the iPhone, convert Live Photos, push each file to the Samsung, confirm it landed,
              and only then clean up the staged copy. You can unplug the iPhone once the relay reports complete.
            </p>
            <div className="dialog-actions">
              <button className="button button-secondary" onClick={onCancel} disabled={busy}>
                Not yet
              </button>
              <button className="button button-primary" onClick={onConfirm} disabled={busy}>
                {busy ? "Starting…" : "Start relay"}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}