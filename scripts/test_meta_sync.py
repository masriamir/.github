#!/usr/bin/env python3
"""Self-test for meta_sync.py.

Builds a canonical source directory and a consuming repository directory under a
tempdir, wires them together with a `file:` manifest, and exercises check/sync for
both modes plus the failure paths. Stdlib only; run directly with python3.
"""

import difflib
import subprocess
import sys
import tempfile
import textwrap
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


def case(name: str, condition: bool, detail: str = "") -> None:
    """Record one assertion, printing `detail` when it fails.

    Each assertion stands alone and carries its own evidence — the subprocess's
    stderr, or a diff of the bytes that disagreed. Bundling several conditions
    into one `case` with `and` would short-circuit, reporting a single opaque
    line that cannot distinguish "sync errored" from "content differs".
    """
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"FAIL  {name}", file=sys.stderr)
        if detail.strip():
            print(textwrap.indent(detail.rstrip("\n"), "      "), file=sys.stderr)


def byte_diff(actual: bytes, expected: bytes) -> str:
    """Unified diff of two byte strings, decoded only for display."""
    return "".join(
        difflib.unified_diff(
            actual.decode("utf-8", "replace").splitlines(keepends=True),
            expected.decode("utf-8", "replace").splitlines(keepends=True),
            "actual",
            "expected",
        )
    )


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
    case("diff direction: canonical is the new file", "+++ canonical" in r.stderr and "--- canonical" not in r.stderr)
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

    # A non-UTF8 manifest fails cleanly (UnicodeDecodeError is a ValueError, not
    # an OSError — load_manifest must still turn it into a clean diagnostic).
    badenc = root / "bad-encoding"
    badenc.mkdir()
    (badenc / ".meta-manifest.toml").write_bytes(b"\xff\xfe not utf-8 toml")
    r = run(badenc, "check")
    case(
        "non-UTF8 manifest fails cleanly",
        r.returncode != 0 and "cannot parse" in r.stderr and "Traceback" not in r.stderr,
    )

    # Comparison is byte-for-byte: a CRLF destination is drift against an LF
    # canonical (text-mode newline translation used to hide this), and sync
    # rewrites it back to the canonical LF bytes. Pin explicit LF bytes for both
    # sides so the test is OS-independent — write_text emits CRLF on Windows,
    # which would corrupt the CRLF/LF distinction this case exists to check.
    lf = b"canonical line 1\ncanonical line 2\ncanonical line 3\n"
    shared_src.write_bytes(lf)
    (repo / "shared.txt").write_bytes(lf.replace(b"\n", b"\r\n"))
    r = run(repo, "check")
    case("CRLF vs LF is caught as drift", r.returncode == 1 and "drift" in r.stderr)
    run(repo, "sync")
    case("sync restores canonical LF bytes", (repo / "shared.txt").read_bytes() == lf)

    # Byte mode carries arbitrary bytes: a non-UTF8 file-mode canonical syncs and
    # checks cleanly (no decode on the sync/check path), and a differing non-UTF8
    # destination is ordinary drift, repaired by sync — not an "unreadable" error.
    binary = canonical / "templates" / "binary.bin"
    binary.write_bytes(b"\x00\x01\xff\xfe\nmixed\r\n")
    (repo / ".meta-manifest.toml").write_text(
        (repo / ".meta-manifest.toml").read_text()
        + f'\n[[file]]\nsource = "file:{canonical}"\npath = "templates/binary.bin"\n'
        'dest = "asset.bin"\nmode = "file"\n'
    )
    run(repo, "sync")
    case("non-UTF8 file-mode canonical syncs byte-exact", (repo / "asset.bin").read_bytes() == binary.read_bytes())
    case("check passes on the binary entry", run(repo, "check").returncode == 0)
    (repo / "asset.bin").write_bytes(b"\xff\xfe\x00 tampered")
    r = run(repo, "check")
    case(
        "differing non-UTF8 destination is drift, not an unreadable error",
        r.returncode == 1 and "drift" in r.stderr and "cannot read" not in r.stderr,
    )
    run(repo, "sync")
    case("sync repairs the tampered binary destination", run(repo, "check").returncode == 0)

    # Block mode converges even when the canonical source lacks a final newline:
    # the body is inserted with a trailing newline so the closing marker keeps its
    # line and check/sync agree (the no-final-newline source used to loop forever).
    nonl = root / "no-final-newline"
    nonl.mkdir()
    (canonical / "templates" / "nonl.txt").write_bytes(b"body line 1\nbody line 2")  # no trailing \n
    (nonl / ".meta-manifest.toml").write_text(
        f'[[file]]\nsource = "file:{canonical}"\npath = "templates/nonl.txt"\n'
        'dest = "conf.txt"\nmode = "block"\nmarker = "seg"\n'
    )
    (nonl / "conf.txt").write_text("top\n# >>> meta:seg\n# <<< meta:seg\nbottom\n")
    run(nonl, "sync")
    case("block sync with no-final-newline source succeeds", run(nonl, "check").returncode == 0)
    case(
        "block sync is idempotent (converges)",
        run(nonl, "sync").returncode == 0 and run(nonl, "check").returncode == 0,
    )
    expected_nonl = "top\n# >>> meta:seg\nbody line 1\nbody line 2\n# <<< meta:seg\nbottom\n"
    case("block body normalized with a trailing newline", (nonl / "conf.txt").read_text() == expected_nonl)

    # Canonical block fragments are nesting-neutral: they carry no leading
    # indentation, and each destination supplies the depth from its own opening
    # marker line. That is what lets one fragment serve adopters that nest
    # differently — the shape of the Codecov policy, where a single status
    # fragment lands under both `project:` and `patch:`, in files that may use
    # two- or four-space YAML. Baking the depth into the canonical file instead
    # would splice wrongly-indented bytes into any file that nests differently,
    # producing invalid YAML that byte-oriented `check` cannot see.
    #
    # Built here in the tempdir rather than read from templates/blocks/: this is
    # a test of the sync mechanism, so it must not fail when a policy value is
    # legitimately edited, and must still run where meta_sync.py is vendored
    # without the canonical tree beside it. Bytes throughout — write_text emits
    # CRLF on Windows and read_text normalizes it away again, which would hide
    # the mixed endings that splicing LF fragment bytes into a CRLF destination
    # produces (the same trap the CRLF case above pins explicitly).
    status_src = canonical / "templates" / "status.yml"
    status_src.write_bytes(b"default:\n  target: 90%\n")

    nested = root / "nested"
    nested.mkdir()
    (nested / ".meta-manifest.toml").write_text(
        f"""
[[file]]
source = "file:{canonical}"
path = "templates/status.yml"
dest = "codecov.yml"
mode = "block"
marker = "project-status"

[[file]]
source = "file:{canonical}"
path = "templates/status.yml"
dest = "codecov.yml"
mode = "block"
marker = "patch-status"
"""
    )
    (nested / "codecov.yml").write_bytes(
        b"coverage:\n"
        b"  status:\n"
        b"    project:\n"
        b"      # >>> meta:project-status\n"
        b"      # <<< meta:project-status\n"
        b"      strict:\n"
        b"        target: 95%\n"
        b"    patch:\n"
        b"      # >>> meta:patch-status\n"
        b"      # <<< meta:patch-status\n"
        b"ignore:\n"
        b'  - "examples/**"\n'
    )
    expected_nested = (
        b"coverage:\n"
        b"  status:\n"
        b"    project:\n"
        b"      # >>> meta:project-status\n"
        b"      default:\n"
        b"        target: 90%\n"
        b"      # <<< meta:project-status\n"
        b"      strict:\n"
        b"        target: 95%\n"
        b"    patch:\n"
        b"      # >>> meta:patch-status\n"
        b"      default:\n"
        b"        target: 90%\n"
        b"      # <<< meta:patch-status\n"
        b"ignore:\n"
        b'  - "examples/**"\n'
    )
    r = run(nested, "sync")
    case("one fragment syncs into two markers", r.returncode == 0, r.stderr)
    nested_actual = (nested / "codecov.yml").read_bytes()
    case(
        "fragment indented to each marker's depth, local siblings preserved",
        nested_actual == expected_nested,
        byte_diff(nested_actual, expected_nested),
    )
    r = run(nested, "check")
    case("check agrees with sync on re-indented blocks", r.returncode == 0, r.stderr)
    r = run(nested, "sync")
    case("re-indented block re-syncs cleanly", r.returncode == 0, r.stderr)
    r = run(nested, "check")
    case("re-indented block sync is idempotent", r.returncode == 0, r.stderr)

    # The same canonical fragment, adopted by a repository that indents with four
    # spaces. Nothing about the fragment changes; only the marker's depth does.
    wide = root / "wide-indent"
    wide.mkdir()
    (wide / ".meta-manifest.toml").write_text(
        f'[[file]]\nsource = "file:{canonical}"\npath = "templates/status.yml"\n'
        'dest = "codecov.yml"\nmode = "block"\nmarker = "project-status"\n'
    )
    (wide / "codecov.yml").write_bytes(
        b"coverage:\n"
        b"    status:\n"
        b"        project:\n"
        b"            # >>> meta:project-status\n"
        b"            # <<< meta:project-status\n"
    )
    expected_wide = (
        b"coverage:\n"
        b"    status:\n"
        b"        project:\n"
        b"            # >>> meta:project-status\n"
        b"            default:\n"
        b"              target: 90%\n"
        b"            # <<< meta:project-status\n"
    )
    r = run(wide, "sync")
    case("four-space adopter syncs the same fragment", r.returncode == 0, r.stderr)
    wide_actual = (wide / "codecov.yml").read_bytes()
    case(
        "fragment re-indented to four-space nesting",
        wide_actual == expected_wide,
        byte_diff(wide_actual, expected_wide),
    )
    r = run(wide, "check")
    case("check passes at four-space nesting", r.returncode == 0, r.stderr)

    # Blank lines inside a fragment stay blank: padding them to the marker's
    # depth would emit trailing whitespace, which many linters reject.
    (canonical / "templates" / "gap.yml").write_bytes(b"first: 1\n\nsecond: 2\n")
    gap = root / "blank-lines"
    gap.mkdir()
    (gap / ".meta-manifest.toml").write_text(
        f'[[file]]\nsource = "file:{canonical}"\npath = "templates/gap.yml"\n'
        'dest = "conf.yml"\nmode = "block"\nmarker = "gap"\n'
    )
    (gap / "conf.yml").write_bytes(b"top:\n  # >>> meta:gap\n  # <<< meta:gap\n")
    r = run(gap, "sync")
    case("fragment with a blank line syncs", r.returncode == 0, r.stderr)
    expected_gap = b"top:\n  # >>> meta:gap\n  first: 1\n\n  second: 2\n  # <<< meta:gap\n"
    gap_actual = (gap / "conf.yml").read_bytes()
    case(
        "blank line kept blank, not padded to trailing whitespace",
        gap_actual == expected_gap,
        byte_diff(gap_actual, expected_gap),
    )

    # Markers at column 0 are unaffected: an un-indented destination gets the
    # fragment bytes verbatim, so existing adopters (.gitignore, AGENTS.md) see
    # no change from re-indentation.
    r = run(repo, "check")
    case("column-0 blocks unchanged by re-indentation", r.returncode == 0, r.stderr)

print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
