# Photo Relay architecture

Photo Relay is a local-first macOS desktop app for moving original iPhone media
to a connected Samsung device. The desktop UI is Tauri + React; it supervises
the established Python device pipeline while that pipeline is migrated into the
versioned `packages/sync-core` package.

## Local runtime data

All mutable data stays in this repository's ignored `runtime/` directory:

- `config.local.json` — this Mac's tool paths and device destination.
- `sync-state.json` — current high-water mark and UI summary.
- `transfers.jsonl` — append-only per-media journal. Each record will include a
  stable source identity, size/hash, destination, verification status, retry
  count, and cleanup result.
- `events.jsonl` — append-only activity events emitted for the desktop UI.
- `logs/` — human-readable troubleshooting output.

JSON is used for small current-state documents. JSONL is used for append-only
event and transfer history, allowing recovery after interruption without a
database server or schema migration.

## Safety rule

No original staging file is eligible for cleanup until the destination has been
verified and a successful JSONL transfer record has been appended.
