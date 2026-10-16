# Phone Bridge (`phone_bridge`)

A modular, cross-project bridge for controlling and transferring files to/from Samsung Android devices over Wi-Fi (SSH) with automatic fallback to USB (ADB).

---

## 💡 Why `phone_bridge`?

When controlling an Android device programmatically:
1. **USB cables tether the device**: You can't keep your phone plugged into your Mac at all times.
2. **Standard ADB shell has UID permission mismatch**: `adb shell` runs as the restricted `shell` UID (`2000`), which cannot access Termux private data (`/data/data/com.termux/files`), its venv, or project-specific keys/tokens.
3. **Unified Execution Context**: Both `phone_bridge` transports (SSH into Termux daemon and `adb shell run-as com.termux`) normalize to the exact same execution context: the Termux UID (`u0_a633` / `10633`) with standard environment variables (`PREFIX`, `HOME`, `PATH`). Any script behaves identically whether over Wi-Fi or USB cable.

---

## 📁 Directory Structure

```text
phone_bridge/
├── bin/
│   ├── bridge             # Unified CLI for status, exec, run, push, pull, setup
│   └── known_hosts        # Auto-managed SSH host key fingerprint cache
├── python/
│   ├── __init__.py        # Python package export
│   └── client.py          # Python Phone wrapper class
├── config.env             # Local configuration (SSH host, port, key, etc.)
├── config.env.example     # Template config
├── termux-setup.sh        # Setup script run on phone
└── README.md              # Architecture & usage guide
```

---

## 🚀 Quick Start

### 1. CLI Usage

From any project or script:
```bash
# Check connectivity and storage
./phone_bridge/bin/bridge status

# Execute a one-liner command inside Termux
./phone_bridge/bin/bridge exec "uptime"

# Run a local bash script inside Termux
./phone_bridge/bin/bridge run ./my_task.sh

# Push a file or directory to phone
./phone_bridge/bin/bridge push ./photo.jpg /storage/emulated/0/DCIM/Camera/photo.jpg

# Pull a file or directory from phone
./phone_bridge/bin/bridge pull /storage/emulated/0/DCIM/Camera/photo.jpg ./downloaded.jpg
```

### 2. Python API

```python
from phone_bridge.python.client import Phone

phone = Phone()

# Check connection
print("Connected:", phone.connected())
print(phone.status())

# Run shell commands
output = phone.exec("df -h /storage/emulated/0")
print(output)

# Transfer files
phone.push("./local_asset.bin", "/data/data/com.termux/files/home/asset.bin")
phone.pull("/data/data/com.termux/files/home/output.log", "./remote_output.log")
```

---

## ⚙️ Configuration (`config.env`)

```ini
# Phone Wi-Fi IP or Tailscale IP
PHONE_SSH_HOST=10.71.107.27
PHONE_SSH_PORT=8023
PHONE_SSH_USER=termux
PHONE_SSH_KEY=$HOME/.ssh/id_ed25519
PHONE_SSH_TIMEOUT=6
PHONE_ADB_SERIAL=
```

### Supported Transports & Networks
- **Local Wi-Fi / Hotspot**: Direct low-latency connection (port `8023`).
- **Tailscale VPN**: Connect when device is outside local Wi-Fi. Put the phone's Tailscale `100.x.y.z` address in `PHONE_SSH_HOST`.
- **USB Cable Fallback**: Automatically used if Wi-Fi/SSH is unreachable.
