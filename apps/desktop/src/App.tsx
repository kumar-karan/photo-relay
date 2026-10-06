import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, FolderOpen, RefreshCw, ShieldCheck, Sparkles, Square, Stethoscope, XCircle } from "lucide-react";
import { BootSequence } from "./components/BootSequence";
import { CountUp } from "./components/CountUp";
import { DeviceCheck } from "./components/DeviceCheck";
import { HistoryPanel } from "./components/HistoryPanel";
import { MilestoneFeed } from "./components/MilestoneFeed";
import { RelayPipeline } from "./components/RelayPipeline";
import { StartDialog } from "./components/StartDialog";
import { StatGrid } from "./components/StatGrid";
import { TransferStream } from "./components/TransferStream";
import { useRelay } from "./lib/useRelay";
import { formatCount, titleCase } from "./lib/format";

type Tab = "activity" | "files" | "log";

export default function App() {
  const { dashboard, events, busy, error, setError, refresh, preflight, startSync, stopSync, reveal } = useRelay();
  const [confirming, setConfirming] = useState(false);
  const [tab, setTab] = useState<Tab>("files");
  const [deviceReport, setDeviceReport] = useState<string[] | null>(null);
  const [checking, setChecking] = useState(false);
  const [booted, setBooted] = useState(false);

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

  const finishBoot = useCallback(() => setBooted(true), []);

  const status = dashboard.running ? "running" : dashboard.phase === "done" ? "done" : dashboard.phase === "failed" ? "failed" : "idle";
  const statusText = dashboard.running ? titleCase(dashboard.phase) : dashboard.engineFound ? "Ready" : "Engine missing";

  const folderName = dashboard.projectRoot.split("/").filter(Boolean).at(-1) ?? "";
  const engineLabel = dashboard.engineVersion === "unknown" ? "engine" : `engine ${dashboard.engineVersion}`;
  const meta = folderName ? `${engineLabel} · ${folderName}` : engineLabel;

  const ready = Boolean(dashboard.devices.iPhone?.online && dashboard.devices.Samsung?.online);

  const bootSteps = [
    { key: "engine", label: "Locating sync engine", ready: dashboard.engineFound || dashboard.projectRoot !== "" },
    { key: "devices", label: "Probing connected devices", ready: Object.keys(dashboard.devices).length > 0 },
    { key: "state", label: "Reading transfer state", ready: dashboard.status !== "" },
  ];

  return (
    <div className="app">
      <AnimatePresence>{!booted && <BootSequence steps={bootSteps} onDone={finishBoot} />}</AnimatePresence>

      <motion.header
        className="titlebar"
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: booted ? 1 : 0, y: booted ? 0 : -6 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
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
      </motion.header>

      <div className="app-body">
        <motion.div
          className="shell"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: booted ? 1 : 0, y: booted ? 0 : 12 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <section className="overview">
            <div className="headline">
              <h1 className="headline-title">
                Photo Relay
              </h1>
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
                  <button className="button button-primary" onClick={() => setConfirming(true)} disabled={!dashboard.engineFound}>
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
                Staged files are removed after confirmation on Samsung
              </p>
            </div>

            <RelayPipeline dashboard={dashboard} />
          </section>

          <StatGrid dashboard={dashboard} />

          <section className="grid">
            <div className="stack">
              <article className="panel">
                <div className="panel-head">
                  <div className="panel-title">
                    <span className="panel-eyebrow">{dashboard.running ? "Live relay" : "Session"}</span>
                    <span className="panel-heading">
                      {tab === "files" ? "Transferred files" : tab === "activity" ? "Milestones" : "Engine log"}
                    </span>
                  </div>
                  <div className="segmented">
                    {(["files", "activity", "log"] as Tab[]).map((value) => (
                      <button
                        key={value}
                        className="segment"
                        data-active={tab === value}
                        onClick={() => setTab(value)}
                        aria-pressed={tab === value}
                      >
                        {value === "files" ? "Files" : value === "activity" ? "Stages" : "Log"}
                      </button>
                    ))}
                  </div>
                </div>

                <AnimatePresence mode="wait">
                  <motion.div
                    key={tab}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                    className="panel-body"
                  >
                    {tab === "files" && <TransferStream transfers={dashboard.transfers} />}
                    {tab === "activity" && <MilestoneFeed events={events} />}
                    {tab === "log" &&
                      (dashboard.latestLog ? (
                        <pre className="console">{dashboard.latestLog}</pre>
                      ) : (
                        <div className="console-empty">No run log yet. Start a relay to create one.</div>
                      ))}
                  </motion.div>
                </AnimatePresence>
              </article>

              <article className="panel">
                <div className="panel-head">
                  <div className="panel-title">
                    <span className="panel-eyebrow">Devices</span>
                    <span className="panel-heading">Preflight report</span>
                  </div>
                  <span className="badge" data-tone={ready ? "ok" : "warn"}>
                    {ready ? "Ready" : "Incomplete"}
                  </span>
                </div>
                <DeviceCheck report={deviceReport} devices={dashboard.devices} />
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
                <span>
                  <CountUp value={dashboard.totalSyncedFiles} format={(value) => formatCount(Math.round(value))} /> files secured in total
                </span>
              </div>
            </article>
          </section>
        </motion.div>
      </div>

      <StartDialog
        open={confirming}
        busy={busy}
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          setConfirming(false);
          void startSync();
        }}
      />

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
                Relay running — {titleCase(dashboard.phase)}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}