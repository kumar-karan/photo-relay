import { motion } from "motion/react";
import { FolderOpen, Sparkles, Square, Stethoscope } from "lucide-react";
import type { Dashboard } from "../types";
import { estimateEta, formatBytes, formatCount, formatDuration, formatRate, percentOf, titleCase } from "../lib/format";

type Props = {
  dashboard: Dashboard;
  checking: boolean;
  busy: boolean;
  onDeviceCheck: () => void;
  onStart: () => void;
  onStop: () => void;
  onReveal: () => void;
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="hero-metric">
      <span className="hero-metric-label">{label}</span>
      <span className="hero-metric-value tnum">{value}</span>
    </div>
  );
}

/**
 * The north star: one progress reading owns the top band.
 *
 * Everything the run needs to be understood at a glance lives here. The
 * secondary numbers are grouped as a right-aligned metric set, and the run
 * controls sit on the same line as the file currently moving.
 */
export function Hero({ dashboard, checking, busy, onDeviceCheck, onStart, onStop, onReveal }: Props) {
  const { running, phase } = dashboard;
  const showProgress = running && dashboard.progressTotal > 0;
  const percent = percentOf(dashboard.completedFiles, dashboard.progressTotal);
  const eta = estimateEta(dashboard.transferredBytes, dashboard.totalBytes, dashboard.rateMbps);
  const ready = Boolean(dashboard.devices.iPhone?.online && dashboard.devices.Samsung?.online);

  return (
    <section className="hero panel" data-running={running}>
      <div className="hero-top">
        <div className="hero-headline">
          {showProgress ? (
            <div className="hero-value">
              <span className="hero-num tnum">{Math.round(percent)}</span>
              <span className="hero-pct">%</span>
            </div>
          ) : (
            <div className="hero-value" data-word="true">
              <span className="hero-word">{running ? titleCase(phase) : titleCase(dashboard.status)}</span>
            </div>
          )}
          <div className="hero-caption">
            {showProgress
              ? `${formatCount(dashboard.completedFiles)} of ${formatCount(dashboard.progressTotal)} files`
              : running
                ? "Preparing the relay"
                : ready
                  ? "Both devices ready"
                  : "Connect both phones to begin"}
          </div>
        </div>

        <div className="hero-metrics">
          <Metric label="Rate" value={formatRate(dashboard.rateMbps)} />
          <Metric label="Time left" value={eta !== null ? formatDuration(eta) : "-"} />
          <Metric label="Moved" value={formatBytes(dashboard.transferredBytes)} />
          <Metric label="Total" value={formatBytes(dashboard.totalBytes)} />
        </div>
      </div>

      <div
        className="hero-bar transfer-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={showProgress ? Math.round(percent) : 0}
        aria-label="Transfer progress"
      >
        <motion.div
          className="transfer-fill"
          data-indeterminate={running && !showProgress}
          initial={false}
          animate={{ width: showProgress ? `${percent}%` : running ? "38%" : "0%" }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
          {running && showProgress && (
            <motion.span
              className="transfer-sheen"
              animate={{ x: ["-120%", "320%"] }}
              transition={{ duration: 1.9, repeat: Infinity, ease: "linear" }}
            />
          )}
        </motion.div>
      </div>

      <div className="hero-foot">
        <div className="hero-current">
          <span className="hero-led" data-on={running} />
          <span className="hero-file mono">{dashboard.currentFile || titleCase(phase)}</span>
        </div>
        <div className="hero-actions">
          <button className="button button-secondary" onClick={onDeviceCheck} disabled={checking || running}>
            <Stethoscope size={14} className={checking ? "spin" : undefined} />
            {checking ? "Checking" : "Device check"}
          </button>
          {running ? (
            <button className="button button-danger" onClick={onStop} disabled={busy}>
              <Square size={13} fill="currentColor" />
              Stop relay
            </button>
          ) : (
            <button className="button button-primary" onClick={onStart} disabled={!dashboard.engineFound}>
              <Sparkles size={14} />
              Start relay
            </button>
          )}
          <button className="button button-ghost" onClick={onReveal}>
            <FolderOpen size={14} />
            Data
          </button>
        </div>
      </div>
    </section>
  );
}
