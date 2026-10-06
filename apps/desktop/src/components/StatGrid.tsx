import { motion } from "motion/react";
import { Activity, CheckCircle2, Clock, Image, Timer } from "lucide-react";
import type { Dashboard } from "../types";
import { formatBytes, formatCount, formatDuration, formatStamp, titleCase } from "../lib/format";
import { CountUp } from "./CountUp";

type Stat = {
  label: string;
  note: string;
  icon: React.ReactNode;
  small?: boolean;
  /** When set, the value animates from its previous number. */
  count?: number;
  /** Static text value, used when the number is not worth animating. */
  value?: string;
};

export function StatGrid({ dashboard }: { dashboard: Dashboard }) {
  const lastRun = dashboard.history.at(-1);

  const stats: Stat[] = [
    {
      label: "Relay state",
      value: dashboard.running ? titleCase(dashboard.phase) : titleCase(dashboard.status),
      note: dashboard.running ? `running ${formatDuration(dashboard.elapsedSeconds)}` : "standing by",
      icon: <Activity size={12} />,
    },
    {
      label: "Photos secured",
      // Animated, because this is the number people watch grow.
      value: "",
      note: "files transferred through this relay",
      icon: <Image size={12} />,
      count: dashboard.totalSyncedFiles,
    },
    {
      label: "Latest capture",
      value: formatStamp(dashboard.lastSyncedTimestamp),
      note: "tracked in local state",
      icon: <Clock size={12} />,
      small: true,
    },
    {
      label: "Last batch",
      note: lastRun ? `files in ${formatDuration(lastRun.durationSeconds)}` : "no completed run yet",
      icon: <CheckCircle2 size={12} />,
      count: lastRun ? lastRun.filesPushed : 0,
    },
  ];

  return (
    <section className="stats">
      {stats.map((stat, index) => (
        <motion.article
          className="panel stat"
          key={stat.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="stat-label">
            {stat.icon}
            {stat.label}
          </div>
          <div className="stat-value tnum" data-size={stat.small ? "sm" : undefined}>
            {stat.count !== undefined ? (
              <CountUp value={stat.count} format={(value) => formatCount(Math.round(value))} />
            ) : (
              stat.value
            )}
          </div>
          <div className="stat-note">{stat.note}</div>
        </motion.article>
      ))}
      {dashboard.running && (
        <motion.article
          className="panel stat"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="stat-label">
            <Timer size={12} />
            Moved this run
          </div>
          <div className="stat-value tnum">{formatBytes(dashboard.transferredBytes)}</div>
          <div className="stat-note">
            {dashboard.errors > 0 ? `${dashboard.errors} error${dashboard.errors === 1 ? "" : "s"} so far` : "no errors so far"}
          </div>
        </motion.article>
      )}
    </section>
  );
}