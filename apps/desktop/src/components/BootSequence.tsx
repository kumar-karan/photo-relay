import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

/** Ordered startup checks. Each line resolves as the app confirms it. */
type BootStep = {
  key: string;
  label: string;
  /** Resolves true when the step is satisfied. */
  ready: boolean;
};

const STEP_MS = 260;

/**
 * Power-on sequence shown while the app resolves its first real state.
 *
 * The dashboard is polled, so the first paint has no device data yet. Rather
 * than showing an empty shell, this walks a short checklist and hands off to
 * the live UI, which makes startup feel deliberate instead of broken.
 */
export function BootSequence({ steps, onDone }: { steps: BootStep[]; onDone: () => void }) {
  const [index, setIndex] = useState(0);

  // Advance only past steps that are ready, so a slow engine cannot be
  // reported as finished before it is.
  const settled = useMemo(() => steps.filter((step) => step.ready).length, [steps]);

  useEffect(() => {
    if (index >= steps.length) return;
    if (steps[index].ready) {
      const timer = window.setTimeout(() => setIndex((value) => value + 1), STEP_MS);
      return () => window.clearTimeout(timer);
    }
    // Poll until this step reports ready.
    const timer = window.setTimeout(() => setIndex((value) => value + 1), STEP_MS * 4);
    return () => window.clearTimeout(timer);
  }, [index, steps]);

  useEffect(() => {
    if (index < steps.length) return;
    const timer = window.setTimeout(onDone, 320);
    return () => window.clearTimeout(timer);
  }, [index, steps.length, onDone]);

  const progress = Math.min(100, Math.round(((index + 1) / steps.length) * 100));

  return (
    <motion.div
      className="boot"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.02 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="boot-inner">
        <motion.div
          className="boot-mark"
          initial={{ scale: 0.86, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="boot-ring" />
          <span className="boot-core" />
        </motion.div>

        <div className="boot-name">Photo Relay</div>
        <div className="boot-sub">Waking the relay</div>

        <div className="boot-steps">
          {steps.map((step, position) => {
            const done = position < index;
            const active = position === index && !done;
            return (
              <motion.div
                className="boot-step"
                key={step.key}
                data-state={done ? "done" : active ? "active" : "pending"}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.24, delay: position * 0.03 }}
              >
                <span className="boot-step-dot" />
                <span className="boot-step-label">{step.label}</span>
              </motion.div>
            );
          })}
        </div>

        <div className="boot-track">
          <motion.div
            className="boot-bar"
            initial={{ width: "0%" }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
      </div>
    </motion.div>
  );
}