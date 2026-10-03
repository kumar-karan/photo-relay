import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { Dashboard, RelayEvent } from "../types";

const EMPTY: Dashboard = {
  running: false,
  engineFound: false,
  phase: "idle",
  totalFiles: 0,
  completedFiles: 0,
  totalBytes: 0,
  transferredBytes: 0,
  rateMbps: 0,
  elapsedSeconds: 0,
  errors: 0,
  currentFile: "",
  devices: {},
  status: "idle",
  totalSyncedFiles: 0,
  lastSyncedTimestamp: "",
  history: [],
  transfers: [],
  recentEvents: [],
  latestLog: "",
  projectRoot: "",
  engineVersion: "",
};

const MAX_EVENTS = 150;
const POLL_MS = 1500;

/**
 * Single source of truth for the UI: a polled dashboard snapshot plus the
 * live event stream. Polling covers state the engine only writes to disk
 * (watermarks, history, journal), while events give instant feedback.
 */
export function useRelay() {
  const [dashboard, setDashboard] = useState<Dashboard>(EMPTY);
  const [events, setEvents] = useState<RelayEvent[]>([]);
  const [live, setLive] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const next = await invoke<Dashboard>("dashboard");
      setDashboard(next);
      setError(null);
      if (!started.current) {
        setEvents(next.recentEvents.slice().reverse());
        started.current = true;
      }
    } catch (cause) {
      setError(String(cause));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, POLL_MS);

    const unlisten = listen<RelayEvent>("relay-event", ({ payload }) => {
      setEvents((current) => [payload, ...current].slice(0, MAX_EVENTS));
      setError(null);
      void refresh();
    });

    return () => {
      window.clearInterval(timer);
      void unlisten.then((off) => off());
    };
  }, [refresh]);

  const preflight = useCallback(async () => {
    setBusy(true);
    try {
      return await invoke<string[]>("preflight");
    } catch (cause) {
      setError(String(cause));
      return [] as string[];
    } finally {
      setBusy(false);
    }
  }, []);

  const startSync = useCallback(async () => {
    setBusy(true);
    try {
      await invoke("start_sync");
      setError(null);
    } catch (cause) {
      setError(String(cause));
    } finally {
      setBusy(false);
      void refresh();
    }
  }, [refresh]);

  const reveal = useCallback(async (target: string) => {
    try {
      await invoke("reveal", { path: target });
    } catch (cause) {
      setError(String(cause));
    }
  }, []);

  return { dashboard, events, live, busy, error, setError, refresh, preflight, startSync, reveal };
}