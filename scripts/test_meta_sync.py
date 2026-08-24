#!/usr/bin/env python3
"""Self-test for meta_sync.py.

Builds a canonical source directory and a consuming repository directory under a
tempdir, wires them together with a `file:` manifest, and exercises check/sync for
both modes plus the failure paths. Stdlib only; run directly with python3.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "meta_sync.py"
passed = failed = 0


def run(cwd: Path, command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), command],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def case(name: str, condition: bool) -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"FAIL  {name}", file=sys.stderr)


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    canonical = root / "canonical"
    (canonical / "templates").mkdir(parents=True)
    shared_src = canonical / "templates" / "shared.txt"
    block_src = canonical / "templates" / "block.txt"
    shared_src.write_text("canonical line 1\ncanonical line 2\n")
    block_src.write_text("shared A\nshared B\n")

    repo = root / "repo"
    repo.mkdir()
    (repo / ".meta-manifest.toml").write_text(
        f"""
[[file]]
source = "file:{canonical}"
path = "templates/shared.txt"
dest = "shared.txt"
mode = "file"

[[file]]
source = "file:{canonical}"
path = "templates/block.txt"
dest = "config.txt"
mode = "block"
marker = "base"
"""
    )

    # Nothing wired up yet: check fails on both entries.
    r = run(repo, "check")
    case("check fails while destinations are missing", r.returncode == 1)
    case("missing destination is named", "destination missing" in r.stderr)

    # sync creates the file-mode dest, then aborts on the unseeded block dest.
    r = run(repo, "sync")
    case("sync aborts on missing block markers", r.returncode != 0)
    case("file-mode dest was still created", (repo / "shared.txt").read_text() == shared_src.read_text())

    # Seed the block markers; sync then fills the block and preserves local content.
    (repo / "config.txt").write_text("local top\n# >>> meta:base\n# <<< meta:base\nlocal bottom\n")
    r = run(repo, "sync")
    case("sync succeeds once markers exist", r.returncode == 0)
    expected = "local top\n# >>> meta:base\nshared A\nshared B\n# <<< meta:base\nlocal bottom\n"
    case("block filled, local content preserved", (repo / "config.txt").read_text() == expected)
    r = run(repo, "check")
    case("check passes when in sync", r.returncode == 0)

    # Local drift in each mode is caught, and sync repairs it.
    (repo / "shared.txt").write_text("tampered\n")
    (repo / "config.txt").write_text("local top\n# >>> meta:base\ntampered\n# <<< meta:base\nlocal bottom\n")
    r = run(repo, "check")
    case("check fails on drift in both modes", r.returncode == 1 and r.stderr.count("drift") == 2)
    run(repo, "sync")
    case("sync repairs drift", run(repo, "check").returncode == 0)

    # A canonical change is drift too, until synced.
    shared_src.write_text("canonical line 1\ncanonical line 2\ncanonical line 3\n")
    case("canonical change shows as drift", run(repo, "check").returncode == 1)
    run(repo, "sync")
    case("sync adopts the canonical change", run(repo, "check").returncode == 0)

    # Usage and missing-manifest paths exit 2.
    case("unknown command exits 2", run(repo, "bogus").returncode == 2)
    empty = root / "empty"
    empty.mkdir()
    case("missing manifest exits 2", run(empty, "check").returncode == 2)

    # Fetch/config failures surface as clean meta_sync messages, never tracebacks.
    bad = root / "badpath"
    bad.mkdir()
    (bad / ".meta-manifest.toml").write_text(
        f"""
[[file]]
source = "file:{canonical}"
path = "templates/missing.txt"
dest = "missing.txt"
mode = "file"
"""
    )
    r = run(bad, "check")
    case(
        "missing canonical path fails cleanly",
        r.returncode != 0 and "meta_sync:" in r.stderr and "Traceback" not in r.stderr,
    )

    badref = root / "badref"
    badref.mkdir()
    (badref / ".meta-manifest.toml").write_text(
        """
[[file]]
source = "masriamir/.github"
ref = "main"
path = "templates/editorconfig"
dest = ".editorconfig"
mode = "file"
"""
    )
    r = run(badref, "check")  # ref validation fires before any network fetch
    case(
        "non-sha ref rejected with a clear message",
        r.returncode != 0 and "40-char commit sha" in r.stderr and "Traceback" not in r.stderr,
    )

    # A malformed manifest fails cleanly too: parse error, wrong shape, missing keys.
    def manifest_case(name: str, toml_text: str, needle: str) -> None:
        d = root / name
        d.mkdir()
        (d / ".meta-manifest.toml").write_text(toml_text)
        r = run(d, "check")
        case(
            f"{name} fails cleanly",
            r.returncode != 0 and needle in r.stderr and "Traceback" not in r.stderr,
        )

    manifest_case("parse-error", "[[file]\n", "cannot parse")
    manifest_case("wrong-shape", 'file = "not a table"\n', "array of tables")
    manifest_case(
        "missing-keys",
        f'[[file]]\nsource = "file:{canonical}"\npath = "templates/block.txt"\n'
        'dest = "config.txt"\nmode = "block"\n',  # block mode without marker
        "missing or non-string key(s): marker",
    )
    manifest_case(
        "bad-mode",
        f'[[file]]\nsource = "file:{canonical}"\npath = "t"\ndest = "d"\nmode = "sideways"\n',
        "mode must be 'file' or 'block'",
    )

    # Unreadable (non-UTF8) destinations and canonical sources fail cleanly too.
    (repo / "shared.txt").write_bytes(b"\xff\xfe\x00 not utf-8")
    r = run(repo, "check")
    case(
        "non-UTF8 destination reported as a per-entry failure",
        r.returncode == 1 and "cannot read" in r.stderr and "Traceback" not in r.stderr,
    )
    run(repo, "sync")  # file mode overwrites without reading the destination
    case("sync restores the non-UTF8 destination", run(repo, "check").returncode == 0)
    block_src.write_bytes(b"\xff\xfe binary")
    r = run(repo, "check")
    case(
        "non-UTF8 canonical fails cleanly",
        r.returncode != 0 and "cannot fetch" in r.stderr and "Traceback" not in r.stderr,
    )
    block_src.write_text("shared A\nshared B\n")

print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
