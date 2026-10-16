"""Talk to the Android phone from Python, over whatever transport is up.

The point of this wrapper is that a project should not care whether the phone is
reachable by SSH or by adb. Both are normalised to "a shell inside Termux",
because that is the only context where the server, its venv and its token live.
`adb shell` on its own runs as the shell uid and cannot see /data/data/com.termux.

    from phone_bridge.python.client import Phone

    phone = Phone()
    phone.exec("ls ~/photo-drop")
    phone.push("./server.py", "/data/data/com.termux/files/home/photo-drop/server.py")
    phone.pull("/data/data/com.termux/files/home/photo-drop/server.log", "./local.log")
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent.parent / "bin" / "bridge"


class BridgeError(RuntimeError):
    """The phone could not be reached, or the command failed."""


class Phone:
    def __init__(self, bridge: Path | str | None = None):
        self.bridge = Path(bridge) if bridge else BRIDGE
        if not self.bridge.exists():
            raise BridgeError(f"bridge script not found at {self.bridge}")

    def _run(self, *args: str, stdin: bytes | None = None) -> str:
        proc = subprocess.run(
            [str(self.bridge), *args],
            input=stdin,
            capture_output=True,
        )
        if proc.returncode != 0:
            # The bridge already writes a legible reason to stderr. Pass it up
            # rather than replacing it with something vaguer.
            detail = (proc.stderr or proc.stdout).decode("utf-8", "replace").strip()
            raise BridgeError(detail or f"bridge {' '.join(args)} failed")
        return proc.stdout.decode("utf-8", "replace")

    def status(self) -> str:
        """Human readable transport report. Raises if nothing is reachable."""
        return self._run("status")

    def connected(self) -> bool:
        try:
            self.status()
            return True
        except BridgeError:
            return False

    def exec(self, command: str) -> str:
        """Run a shell command inside Termux and return its stdout."""
        return self._run("exec", command)

    def run_script(self, local_script: str | os.PathLike) -> str:
        """Run a local shell script inside Termux."""
        path = Path(local_script)
        if not path.is_file():
            raise BridgeError(f"no such script: {path}")
        return self._run("run", str(path))

    def push(self, local: str | os.PathLike, remote: str) -> str:
        """Copy a file or directory onto the phone.

        With the adb transport the destination must be inside Termux's home or
        /sdcard. There is no shared filesystem between the two, so the bridge
        stages through /sdcard rather than pretending otherwise.
        """
        return self._run("push", str(local), remote)

    def pull(self, remote: str, local: str | os.PathLike) -> str:
        """Copy a file or directory from the phone to local machine."""
        return self._run("pull", remote, str(local))


if __name__ == "__main__":
    import sys

    p = Phone()
    try:
        if len(sys.argv) > 1:
            print(p.exec(sys.argv[1]), end="")
        else:
            print(p.status())
    except BridgeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
