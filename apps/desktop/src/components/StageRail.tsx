import { Check } from "lucide-react";
import type { Dashboard } from "../types";

/** The relay's fixed stages, in order. */
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

/**
 * A slim, single-line stepper for where the run is.
 *
 * Deliberately one row: a full vertical timeline spends too much space on a
 * mostly static list, and a live transfer is better served by the progress
 * reading above it.
 */
export function StageRail({ dashboard }: { dashboard: Dashboard }) {
  return (
    <section className="panel stage-strip">
      <div className="stages">
        {STAGES.map((stage) => {
          const state = stageState(stage.key, dashboard.phase, dashboard.running);
          return (
            <div className="stage" key={stage.key} data-state={state}>
              <span className="stage-dot">{state === "done" && <Check size={9} strokeWidth={3} />}</span>
              <span className="stage-label">{stage.label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
