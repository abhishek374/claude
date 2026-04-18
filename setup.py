#!/usr/bin/env python3
"""
One-command local setup for the LinkedIn Search MCP server.

Run: python setup.py
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def run(cmd, **kwargs):
    print(f"  $ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    subprocess.run(cmd, check=True, shell=isinstance(cmd, str), **kwargs)


def step(msg):
    print(f"\n{'─'*60}\n  {msg}\n{'─'*60}")


# ── 1. virtual environment ────────────────────────────────────────────────────

step("1 / 4  Creating virtual environment")
venv_dir = Path(".venv")
if not venv_dir.exists():
    run([sys.executable, "-m", "venv", str(venv_dir)])
    print("  Created .venv/")
else:
    print("  .venv/ already exists — skipping")

# path to the venv's python / pip
if platform.system() == "Windows":
    venv_python = str(venv_dir / "Scripts" / "python.exe")
    venv_pip    = str(venv_dir / "Scripts" / "pip.exe")
else:
    venv_python = str(venv_dir / "bin" / "python")
    venv_pip    = str(venv_dir / "bin" / "pip")

# ── 2. install dependencies ───────────────────────────────────────────────────

step("2 / 4  Installing dependencies")
run([venv_pip, "install", "-q", "-r", "requirements.txt"])
print("  Dependencies installed.")

# ── 3. create .env ────────────────────────────────────────────────────────────

step("3 / 4  Configuring .env")
env_path = Path(".env")
if not env_path.exists():
    cookie = input(
        "\n  Paste your LinkedIn li_at cookie value\n"
        "  (Chrome → F12 → Application → Cookies → linkedin.com → li_at):\n  > "
    ).strip()
    env_path.write_text(f"LINKEDIN_COOKIE={cookie}\n")
    print("  .env created.")
else:
    print("  .env already exists — skipping")

# ── 4. generate Claude Desktop config snippet ─────────────────────────────────

step("4 / 4  Generating Claude Desktop MCP config")

repo_dir = str(Path(__file__).parent.resolve())
mcp_entry = {
    "linkedin-search": {
        "command": venv_python,
        "args": ["-m", "src.server"],
        "cwd": repo_dir,
    }
}

# Detect config path
system = platform.system()
if system == "Darwin":
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
elif system == "Windows":
    config_path = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
else:
    config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

# Merge into existing config if present
if config_path.exists():
    existing = json.loads(config_path.read_text())
else:
    existing = {}

existing.setdefault("mcpServers", {}).update(mcp_entry)
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(existing, indent=2))
print(f"  Written to: {config_path}")

# ── done ──────────────────────────────────────────────────────────────────────

print(f"""
{'='*60}
  Setup complete!

  Next steps:
    1. Run the test to confirm LinkedIn access works:
         {venv_python} test_search.py

    2. Restart Claude Desktop — the "linkedin-search" MCP
       server will appear automatically.

    3. Ask Claude things like:
         "Search LinkedIn for ML engineers at Google in London"
         "Find fintech companies in Singapore"
         "Get the LinkedIn profile for satyanadella"
{'='*60}
""")
