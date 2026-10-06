import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, Cpu, HardDrive, Smartphone, XCircle } from "lucide-react";
import type { Dashboard } from "../types";

type Parsed = { label: string; online: boolean };

/**
 * Turn the engine's probe output into structured rows.
 *
 * The detector prints one labelled line per device followed by a mode line, so
 * the text is split on its separator rather than matched on wording.
 */
function parseReport(lines: string[]): { devices: Parsed[]; mode: string } {
  const devices: Parsed[] = [];
  let mode = "";

  for (const line of lines) {
    const separator = line.includes(" : ") ? " : " : line.includes(": ") ? ": " : null;
    if (!separator) {
      if (/mode/i.test(line) && line.includes("(")) mode = line;
      continue;
    }
    const index = line.indexOf(separator);
    const label = line.slice(0, index).trim();
    const value = line.slice(index + separator.length).trim();
    if (/iphone/i.test(label)) devices.push({ label: "iPhone", online: !/^no\b/i.test(value) });
    else if (/samsung/i.test(label)) devices.push({ label: "Samsung", online: !/^no\b/i.test(value) });
  }

  return { devices, mode };
}

export function DeviceCheck({
  report,
  devices,
}: {
  report: string[] | null;
  devices: Record<string, { online: boolean; detail: string }>;
}) {
  const parsed = parseReport(report ?? []);
  // Prefer the live dashboard so the panel still works before a check runs.
  const rows = parsed.devices.length
    ? parsed.devices
    : Object.entries(devices).map(([label, state]) => ({ label, online: state.online }));

  return (
    <div className="check">
      <AnimatePresence mode="popLayout">
        {rows.map((row, index) => {
          const live = devices[row.label];
          const online = live ? live.online : row.online;
          return (
            <motion.div
              className="check-row"
              key={row.label}
              data-online={online}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.26, delay: index * 0.05, ease: [0.22, 1, 0.36, 1] }}
            >
              <span className="check-icon">
                {row.label === "iPhone" ? <Smartphone size={14} /> : <HardDrive size={14} />}
              </span>
              <div className="check-body">
                <div className="check-label">{row.label}</div>
                <div className="check-detail">{live?.detail ?? (online ? "Connected" : "Not detected")}</div>
              </div>
              <span className="check-state" data-online={online}>
                {online ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                {online ? "Ready" : "Missing"}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>

      <div className="check-foot">
        <span className="check-foot-icon">
          <Cpu size={12} />
        </span>
        <span>{parsed.mode || "Waiting for a device check"}</span>
      </div>
    </div>
  );
}