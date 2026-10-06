"""Offline installer selection check: python3 scripts/test_setup.py."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


setup = Path(__file__).with_name("setup").read_text()
install = setup[setup.index("install_python_packages() {"):setup.index("write_environment() {")]
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bin_dir = root / "venv with spaces" / "bin"
    bin_dir.mkdir(parents=True)
    log = root / "calls.jsonl"
    mock = """#!/usr/bin/python3
import json, os, sys
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps(sys.argv) + '\\n')
if sys.argv[1:] == ['-m', 'pip', '--version']:
    sys.exit(int(os.environ['MISSING_PIP']))
"""
    python = bin_dir / "python"
    python.write_text(mock)
    python.chmod(0o755)
    for use_uv, missing_pip in [(True, True), (False, False), (False, True)]:
        uv = bin_dir / "uv"
        if use_uv:
            uv.write_text(mock)
            uv.chmod(0o755)
        else:
            uv.unlink(missing_ok=True)
        log.write_text("")
        subprocess.run(
            ["/bin/bash", "-c", 'set -eu; VENV="$1"; WS="$2"; CONTEXT=mujoco\n'
             + install + '\ninstall_python_packages', "check", str(bin_dir.parent), str(root)],
            env={**os.environ, "PATH": str(bin_dir), "CALL_LOG": str(log),
                 "MISSING_PIP": str(int(missing_pip))}, check=True,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        prefix = ([str(uv), "pip", "install", "--python", str(python)] if use_uv
                  else [str(python), "-m", "pip", "install"])
        installs = [call for call in calls if call[:len(prefix)] == prefix]
        assert len(installs) == 9, calls
        assert "zstandard" in installs[0]
        assert installs[-1][len(prefix):] == ["--no-deps", "-e", str(root / "pydeps/motion-spec")]
        assert ([str(python), "-m", "ensurepip", "--upgrade"] in calls) == (missing_pip and not use_uv)
print("PASS: uv, pip, and pip bootstrap for an existing uv-created venv")
