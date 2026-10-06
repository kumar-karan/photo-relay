import { motion } from "motion/react";
import { Check, HardDrive, Laptop, Smartphone, Zap } from "lucide-react";
import type { Dashboard } from "../types";
import { estimateEta, formatBytes, formatCount, formatDuration, formatRate, percentOf, titleCase } from "../lib/format";

/** Phases where bytes are actually moving, so the beam animates. */
const FLOWING = new Set(["downloading", "converting", "transferring", "pushing", "indexing"]);

/** The relay's fixed stages, in order, for the pipeline rail. */
const STAGES = [
  { key: "connecting", label: "Connect" },
  { key: "scanning", label: "Scan" },
  { key: "downloading", label: "Pull" },
  { key: "converting", label: "Convert" },
  { key: "pushing", label: "Push" },
  { key: "indexing", label: "Index" },
] as const;

type StageState = "pending" | "active" | "done";

function stageState(stage: string, phase: string, running: boolean): StageState {
  if (!running) return "pending";
  const current = STAGES.findIndex((item) => item.key === phase);
  const at = STAGES.findIndex((item) => item.key === stage);
  if (current < 0) return "pending";
  if (at < current) return "done";
  if (at === current) return "active";
  return "pending";
}

export function RelayPipeline({ dashboard }: { dashboard: Dashboard }) {
  const { devices, phase, running } = dashboard;
  const flowing = running && FLOWING.has(phase);
  const showProgress = running && dashboard.progressTotal > 0;
  const percent = percentOf(dashboard.completedFiles, dashboard.progressTotal);
  const eta = estimateEta(dashboard.transferredBytes, dashboard.totalBytes, dashboard.rateMbps);

  const iphone = devices.iPhone;
  const samsung = devices.Samsung;

  const ready = Boolean(iphone?.online && samsung?.online);

  const nodes = [
    {
      key: "iphone",
      label: "iPhone",
      detail: iphone?.online ? iphone.detail : "Not detected",
      icon: <Smartphone size={18} />,
      online: Boolean(iphone?.online),
      active: flowing && (phase === "downloading" || phase === "converting"),
    },
    {
      key: "mac",
      label: "This Mac",
      detail: running ? titleCase(phase) : "Standing by",
      icon: <Laptop size={18} />,
      online: true,
      active: flowing,
    },
    {
      key: "samsung",
      label: "Samsung",
      detail: samsung?.online ? samsung.detail : "Not detected",
      icon: <HardDrive size={18} />,
      online: Boolean(samsung?.online),
      active: flowing && (phase === "pushing" || phase === "indexing"),
    },
  ];

  return (
    <section className="panel pipeline" data-flowing={flowing}>
      {/* Device chain with animated links */}
      <div className="pipeline-track">
        {nodes.map((node, index) => (
          <div key={node.key} className="pipeline-slot">
            {index > 0 && (
              <div className="pipeline-link" data-active={node.active || nodes[index - 1].active}>
                <div className="pipeline-link-track">
                  <motion.div
                    className="pipeline-link-pulse"
                    animate={node.active || nodes[index - 1].active ? { x: ["-100%", "200%"] } : { x: "-100%" }}
                    transition={
                      node.active || nodes[index - 1].active
                        ? { duration: 1.5, repeat: Infinity, ease: "linear" }
                        : { duration: 0 }
                    }
                  />
                </div>
              </div>
            )}
            <motion.div
              className="pipeline-node"
              data-online={node.online}
              data-active={node.active}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.07, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="pipeline-node-icon">
                <span className="pipeline-node-halo" />
                {node.icon}
              </div>
              <div className="pipeline-node-text">
                <div className="pipeline-node-label">{node.label}</div>
                <div className="pipeline-node-detail">{node.detail}</div>
              </div>
              <span className="pipeline-node-led" data-on={node.online} />
            </motion.div>
          </div>
        ))}
      </div>

      {/* Stage rail */}
      <div className="stages">
        {STAGES.map((stage) => {
          const state = stageState(stage.key, phase, running);
          return (
            <div className="stage" key={stage.key} data-state={state}>
              <span className="stage-dot">
                {state === "done" && <Check size={9} strokeWidth={3} />}
              </span>
              <span className="stage-label">{stage.label}</span>
            </div>
          );
        })}
      </div>

      {/* Transfer progress */}
      <div className="transfer">
        <div className="transfer-head">
          <div className="transfer-file" title={dashboard.currentFile}>
            {dashboard.currentFile || titleCase(phase)}
          </div>
          <div className="transfer-readout">
            {showProgress && (
              <>
                <span className="transfer-count">
                  {formatCount(dashboard.completedFiles)}
                  <span className="transfer-count-sep">/</span>
                  {formatCount(dashboard.progressTotal)}
                </span>
                <span className="transfer-rate">{formatRate(dashboard.rateMbps)}</span>
                {eta !== null && <span className="transfer-eta">{formatDuration(eta)} left</span>}
              </>
            )}
            {!running && dashboard.status !== "idle" && <span className="transfer-final">{titleCase(dashboard.status)}</span>}
          </div>
        </div>

        <div
          className="transfer-track"
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
            {flowing && showProgress && (
              <motion.span
                className="transfer-sheen"
                animate={{ x: ["-120%", "320%"] }}
                transition={{ duration: 1.9, repeat: Infinity, ease: "linear" }}
              />
            )}
          </motion.div>
        </div>

        <div className="transfer-foot">
          {showProgress ? (
            <>
              <span>
                {formatBytes(dashboard.transferredBytes)} of {formatBytes(dashboard.totalBytes)}
              </span>
              <span className="transfer-percent">{percent.toFixed(0)}%</span>
            </>
          ) : running ? (
            <span className="transfer-hint">Preparing the relay</span>
          ) : (
            <span className="transfer-hint">{ready ? "Both devices ready" : "Connect both phones to begin"}</span>
          )}
        </div>
      </div>
    </section>
  );
}