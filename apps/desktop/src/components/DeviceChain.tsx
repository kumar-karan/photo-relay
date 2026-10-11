import { motion } from "motion/react";
import { HardDrive, Laptop, Smartphone } from "lucide-react";
import type { Dashboard } from "../types";
import { titleCase } from "../lib/format";

/** Phases where bytes are actually moving, so the links animate. */
const FLOWING = new Set(["downloading", "converting", "transferring", "pushing", "indexing"]);

/**
 * Source to destination rail: iPhone, this Mac, Samsung.
 *
 * This is the relay's mental model drawn once, horizontally. The stage rail is
 * kept separate so the two never repeat each other.
 */
export function DeviceChain({ dashboard }: { dashboard: Dashboard }) {
  const { devices, phase, running } = dashboard;
  const flowing = running && FLOWING.has(phase);
  const iphone = devices.iPhone;
  const samsung = devices.Samsung;

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
    <section className="panel chain" data-flowing={flowing}>
      <div className="pipeline-track">
        {nodes.map((node, index) => (
          <div key={node.key} className="pipeline-slot">
            {index > 0 && (
              <div className="pipeline-link" data-active={node.active || nodes[index - 1].active}>
                <div className="pipeline-link-track">
                  <div className="pipeline-link-pulse" />
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
    </section>
  );
}
