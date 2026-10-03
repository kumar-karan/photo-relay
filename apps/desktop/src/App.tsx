import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, FolderOpen, Radio, RefreshCw, ScrollText, ShieldCheck, Sparkles, Square, Stethoscope, XCircle } from "lucide-react";
import { ActivityFeed } from "./components/ActivityFeed";
import { HistoryPanel, VerifiedPanel } from "./components/HistoryPanel";
import { RelayMap } from "./components/RelayMap";
import { StartDialog } from "./components/StartDialog";
import { StatGrid } from "./components/StatGrid";
import { useRelay } from "./lib/useRelay";
import { titleCase } from "./lib/format";

type Tab = "activity" | "log";

export default function App() {
  const { dashboard, events, busy, error, setError, refresh, preflight, startSync, stopSync, reveal } = useRelay();
  const [confirming, setConfirming] = useState(false);
  const [tab, setTab] = useState<Tab>("activity");
  const [deviceReport, setDeviceReport] = useState<string[] | null>(null);
  const [checking, setChecking] = useState(false);

  // ⌘R refreshes, ⌘↵ starts a relay, Esc dismisses dialogs and reports.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const meta = event.metaKey || event.ctrlKey;
      if (meta && event.key.toLowerCase() === "r") {
        event.preventDefault();
        void refresh();
      } else if (meta && event.key === "Enter" && dashboard.engineFound && !dashboard.running) {
        event.preventDefault();
        setConfirming(true);
      } else if (event.key === "Escape") {
        setConfirming(false);
        setDeviceReport(null);
        setError(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dashboard.engineFound, dashboard.running, refresh, setError]);

  const runDeviceCheck = async () => {
    setChecking(true);
    setDeviceReport(await preflight());
    setChecking(false);
  };

  const status = dashboard.running ? "running" : dashboard.phase === "done" ? "done" : dashboard.phase === "failed" ? "failed" : "idle";
  const statusText = dashboard.running
    ? titleCase(dashboard.phase)
    : dashboard.engineFound
      ? "Ready"
      : "Engine missing";

  // Show the project folder name, not a truncated tail of its path. The full
  // path stays available as a tooltip.
  const folderName = dashboard.projectRoot.split("/").filter(Boolean).at(-1) ?? "";
  const engineLabel = dashboard.engineVersion === "unknown" ? "engine" : `engine ${dashboard.engineVersion}`;
  const meta = folderName ? `${engineLabel} · ${folderName}` : engineLabel;

  return (
    <div className="app">
      <header className="titlebar">
        <div className="identity">
          <div className="identity-mark">
            <Sparkles size={14} />
          </div>
          <div className="identity-text">
            <span className="identity-name">Photo Relay</span>
            <span className="identity-meta" title={dashboard.projectRoot}>
              {meta}
            </span>
          </div>
        </div>
        <div className="titlebar-actions">
          <span className="status-pill" data-state={status}>
            <span className="status-dot" />
            {statusText}
          </span>
          <button className="button button-icon" onClick={() => void refresh()} aria-label="Refresh">
            <RefreshCw size={14} className={busy ? "spin" : undefined} />
          </button>
        </div>
      </header>

      <div className="app-body">
        <div className="shell">
          <section className="overview">
            <div className="headline">
              <span className="headline-eyebrow">
                <Radio size={11} />
                Local photo bridge
              </span>
              <h1 className="headline-title">
                One path for <em>every</em> capture.
              </h1>
              <p className="headline-copy">
                Original photos, videos and Live Photos move from your iPhone to the Samsung with capture times intact. Nothing leaves this
                Mac.
              </p>
              <div className="headline-actions">
                <button className="button button-secondary" onClick={() => void runDeviceCheck()} disabled={checking || dashboard.running}>
                  <Stethoscope size={14} className={checking ? "spin" : undefined} />
                  {checking ? "Checking…" : "Device check"}
                </button>
                {dashboard.running ? (
                  <button className="button button-danger" onClick={() => void stopSync()} disabled={busy}>
                    <Square size={13} fill="currentColor" />
                    Stop relay
                  </button>
                ) : (
                  <button
                    className="button button-primary"
                    onClick={() => setConfirming(true)}
                    disabled={!dashboard.engineFound}
                  >
                    <Sparkles size={14} />
                    Start relay
                  </button>
                )}
                <button className="button button-ghost" onClick={() => void reveal("runtime")}>
                  <FolderOpen size={14} />
                  Data
                </button>
              </div>
              <p className="hint">
                <ShieldCheck size={12} />
                Staged files are only removed after the transfer is confirmed on the Samsung.
              </p>
            </div>

            <RelayMap dashboard={dashboard} />
          </section>

          <StatGrid dashboard={dashboard} />

          <section className="grid">
            <div className="stack">
              <article className="panel">
                <div className="panel-head">
                  <div className="panel-title">
                    <span className="panel-eyebrow">{dashboard.running ? "Live relay" : "Session"}</span>
                    <span className="panel-heading">Transfer activity</span>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    {(["activity", "log"] as Tab[]).map((value) => (
                      <button
                        key={value}
                        className={`button ${tab === value ? "button-secondary" : "button-ghost"}`}
                        onClick={() => setTab(value)}
                        aria-pressed={tab === value}
                      >
                        {value === "activity" ? <ScrollText size={13} /> : <FolderOpen size={13} />}
                        {value === "activity" ? "Activity" : "Log"}
                      </button>
                    ))}
                  </div>
                </div>

                {deviceReport && (
                  <div className="console" style={{ borderRadius: 0, maxHeight: 150 }}>
                    {deviceReport.length ? deviceReport.join("\n") : "No devices reported."}
                  </div>
                )}

                {tab === "activity" ? (
                  <ActivityFeed events={events} />
                ) : (
                  <pre className="console">
                    {dashboard.latestLog || <span className="console-empty">No run log yet. Start a relay to create one.</span>}
                  </pre>
                )}
              </article>

              <article className="panel">
                <div className="panel-head">
                  <div className="panel-title">
                    <span className="panel-eyebrow">Verified</span>
                    <span className="panel-heading">Transferred this session</span>
                  </div>
                  <span className="badge">{dashboard.transfers.length}</span>
                </div>
                <VerifiedPanel transfers={dashboard.transfers} onReveal={() => void reveal("runtime")} />
              </article>
            </div>

            <article className="panel">
              <div className="panel-head">
                <div className="panel-title">
                  <span className="panel-eyebrow">Local history</span>
                  <span className="panel-heading">Recent runs</span>
                </div>
                <button className="button button-ghost" onClick={() => void reveal("logs")}>
                  <FolderOpen size={13} />
                  Logs
                </button>
              </div>
              <HistoryPanel history={dashboard.history} />
              <div className="panel-foot">
                <span>Watermark tracked in sync_engine/sync_state.json</span>
              </div>
            </article>
          </section>
        </div>
      </div>

      <StartDialog open={confirming} busy={busy} onCancel={() => setConfirming(false)} onConfirm={() => {
        setConfirming(false);
        void startSync();
      }} />

      <div className="toast-stack">
        <AnimatePresence>
          {error && (
            <motion.div
              className="toast"
              data-tone="error"
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              <span className="toast-glyph">
                <XCircle size={14} />
              </span>
              <div>{error}</div>
              <button className="button button-ghost" onClick={() => setError(null)} aria-label="Dismiss">
                Dismiss
              </button>
            </motion.div>
          )}
        </AnimatePresence>
        <AnimatePresence>
          {!error && dashboard.running && (
            <motion.div
              className="toast"
              data-tone="success"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.22 }}
            >
              <span className="toast-glyph">
                <CheckCircle2 size={14} />
              </span>
              <div>
                Relay running — {titleCase(dashboard.phase)}. Leave both phones connected.
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}