import { motion } from "motion/react";
import { HardDrive, Laptop, Smartphone } from "lucide-react";
import type { Dashboard } from "../types";
import { estimateEta, formatBytes, formatCount, formatDuration, formatRate, percentOf, titleCase } from "../lib/format";

type NodeSpec = {
  key: string;
  label: string;
  detail: string;
  icon: React.ReactNode;
  online: boolean;
};

/** Phases that mean "data is moving" drive the animated link sweep. */
const FLOWING_PHASES = new Set(["downloading", "converting", "transferring", "pushing", "indexing"]);

export function RelayMap({ dashboard }: { dashboard: Dashboard }) {
  const { devices, phase, running } = dashboard;
  const flowing = running && FLOWING_PHASES.has(phase);
  const showProgress = running && dashboard.progressTotal > 0;
  // Rust supplies the denominator that matches the phase, because downloads
  // count source files while pushes count media items.
  const percent = percentOf(dashboard.completedFiles, dashboard.progressTotal);
  const eta = estimateEta(dashboard.transferredBytes, dashboard.totalBytes, dashboard.rateMbps);

  const iphone = devices.iPhone;
  const samsung = devices.Samsung;

  const nodes: NodeSpec[] = [
    {
      key: "iphone",
      label: "iPhone",
      detail: iphone?.online ? iphone.detail : "Not detected",
      icon: <Smartphone size={17} />,
      online: Boolean(iphone?.online),
    },
    {
      key: "mac",
      label: "This Mac",
      // The Mac is always present; it stages and converts, so never call it offline.
      detail: running ? "Staging" : "Standing by",
      icon: <Laptop size={17} />,
      online: true,
    },
    {
      key: "samsung",
      label: "Samsung",
      detail: samsung?.online ? samsung.detail : "Not detected",
      icon: <HardDrive size={17} />,
      online: Boolean(samsung?.online),
    },
  ];

  const links = [
    { label: flowing && (phase === "downloading" || phase === "transferring") ? "Pulling" : "Staged" },
    { label: flowing && phase !== "downloading" ? "Pushing" : "Queued" },
  ];

  return (
    <section className="panel relay" data-active={flowing}>
      <div className="relay-track">
        {nodes.map((node, index) => (
          <div key={node.key} style={{ display: "contents" }}>
            {index > 0 && (
              <div className="link">
                <div className="link-track">
                  <div className="link-fill" />
                </div>
                <span className="link-label">{links[index - 1].label}</span>
              </div>
            )}
            <motion.div
              className="node"
              data-online={node.online}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="node-icon">{node.icon}</div>
              <div>
                <div className="node-label">{node.label}</div>
                <div className="node-state">{node.detail}</div>
              </div>
            </motion.div>
          </div>
        ))}
      </div>

      <div className="progress">
        <div className="progress-head">
          <span className="progress-file">
            {dashboard.currentFile || titleCase(dashboard.phase)}
          </span>
          <span className="progress-stats">
            {showProgress && (
              <>
                <span className="mono">
                  {formatCount(dashboard.completedFiles)}/{formatCount(dashboard.progressTotal)}
                </span>
                <span className="mono">{formatRate(dashboard.rateMbps)}</span>
                {eta !== null && <span className="mono">{formatDuration(eta)} left</span>}
              </>
            )}
            {!running && dashboard.status !== "idle" && <span className="mono">{titleCase(dashboard.status)}</span>}
          </span>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={showProgress ? Math.round(percent) : 0}
          aria-label="Relay progress"
        >
          <motion.div
            className="progress-bar"
            data-indeterminate={running && !showProgress}
            initial={false}
            animate={{ width: showProgress ? `${percent}%` : running ? "34%" : "0%" }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
        {showProgress && (
          <div className="progress-stats" style={{ marginTop: 8, justifyContent: "space-between" }}>
            <span className="mono">
              {formatBytes(dashboard.transferredBytes)} of {formatBytes(dashboard.totalBytes)}
            </span>
            <span className="mono">{percent.toFixed(0)}%</span>
          </div>
        )}
      </div>
    </section>
  );
}