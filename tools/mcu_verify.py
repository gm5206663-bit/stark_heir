#!/usr/bin/env python3
"""MCU Varun fic — project-integrity validator (kit 09 adapted + SL4 manifest check).

Stdlib only. Checks that EXECUTE (kit 09 honesty rule: every gate names its
function and evidence; a clean exit with wrong output is not a pass).

Gates (scope honestly limited, cf. kit 09 §3 scope table):
  G1  zero unreadable-script chars (CJK/kana/hangul) — all project text files
  G2  zero literal backslash-n sequences — all project text files
  G3  zero digits in chapter prose (outside fenced blocks) — chapters only
  G4  >=3 spoken dialogue lines per chapter (outside fences) — chapters only
  G5  panel anchor order (FORGE-first-only, then non-decreasing BCE/CE) — chapters
      LIMIT: single-anchor panels; full span-contiguity needs start-end panels
      (added when arcs span years). Documented, not silently weak.
  G6  zero placeholders (TBD/TODO/FIXME/XXX) — chapters only (foundation may plan)
  G7  marker discipline — chapters: panel fence holds the marker; prose holds none;
      at most one END OF card, last in file
  M1  manifest edge matches chapters on disk
  M2  forbidden-future denylist absent from chapters (per manifest forbidden_now)

Usage:
  python3 tools/mcu_verify.py            # check project
  python3 tools/mcu_verify.py --selftest # 9 fixtures: 8 defects caught + 1 clean pass
Exit: 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ROOT / "chapters"
MANIFEST = ROOT / "foundation" / "CURRENT_STATE_MANIFEST.json"

CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
BACKSLASH_N = chr(92) + "n"  # never write the literal sequence (kit 07 §1)
DIGITS = re.compile(r"[0-9]")
PLACEHOLDER = re.compile(r"\b(TBD|TODO|FIXME|XXX|T\.B\.D\.)\b")
PANEL_FIRST = re.compile(r"◆\s*STATUS\s*[—-]\s*Chapter\s+([^:]+):\s*(.+)", re.UNICODE)
BC_YEAR = re.compile(r"(\d+)\s*BC")
CE_YEAR = re.compile(r"(?<!\d)(\d{3,4})(?!\s*BC)")
FUTURE_DENY = ["Chitauri", "Ultron", "Extremis", "Vibranium", "Sokovia", "Blip", "Thanos", "Avengers", "Infinity"]  # shrink as canon is consumed


def split_prose(text: str) -> tuple[str, list[str]]:
    """Kit 09 §4 RIGHT pattern: prose = outside ALL fenced blocks."""
    parts = text.split("```")
    prose = "".join(parts[i] for i in range(0, len(parts), 2))
    fenced = [parts[i] for i in range(1, len(parts), 2)]
    return prose, fenced


def text_files() -> list[Path]:
    out: list[Path] = []
    for sub in ("", "foundation", "bible", "codex", "chapters", "tools", "audits"):
        d = ROOT / sub if sub else ROOT
        if not d.is_dir():
            continue
        for ext in ("*.md", "*.json", "*.py"):
            out.extend(sorted(d.glob(ext)))
    return out


def chapter_files() -> list[Path]:
    return sorted(CHAPTERS.glob("Chapter_*.md")) if CHAPTERS.is_dir() else []


class Gate:
    def __init__(self, name: str):
        self.name = name
        self.fails: list[str] = []
        self.info: list[str] = []

    def fail(self, msg: str):
        self.fails.append(msg)

    def note(self, msg: str):
        self.info.append(msg)

    def ok(self) -> bool:
        return not self.fails


def g1_unreadable() -> Gate:
    g = Gate("G1 unreadable-script")
    for f in text_files():
        s = f.read_text(encoding="utf-8")
        for i, ln in enumerate(s.splitlines(), 1):
            m = CJK.search(ln)
            if m:
                g.fail(f"{f.relative_to(ROOT)}:{i}: {m.group(0)!r}")
    if g.ok():
        g.note(f"scanned {len(text_files())} files, 0 hits (check: CJK regex per line)")
    return g


def g2_backslash_n() -> Gate:
    g = Gate("G2 backslash-n")
    for f in text_files():
        if f.name == "mcu_verify.py":
            continue  # the check must not match its own description (kit 09 §3)
        s = f.read_text(encoding="utf-8")
        if BACKSLASH_N in s:
            g.fail(f"{f.relative_to(ROOT)}: literal sequence present")
    if g.ok():
        g.note("scanned project text (self excluded by scope rule), 0 hits")
    return g


def g3_digits() -> Gate:
    g = Gate("G3 digits-in-prose")
    for f in chapter_files():
        prose, _ = split_prose(f.read_text(encoding="utf-8"))
        for i, ln in enumerate(prose.splitlines(), 1):
            m = DIGITS.search(ln)
            if m:
                g.fail(f"{f.name}:{i}: digit {m.group(0)!r} in {ln.strip()[:60]!r}")
    if g.ok():
        g.note(f"{len(chapter_files())} chapters, prose outside fences, 0 digits")
    return g


def g4_dialogue() -> Gate:
    g = Gate("G4 dialogue-floor")
    for f in chapter_files():
        prose, _ = split_prose(f.read_text(encoding="utf-8"))
        n = sum(1 for ln in prose.splitlines() if '"' in ln or '\u201c' in ln)
        if n < 3:
            g.fail(f"{f.name}: {n} dialogue lines (<3)")
        else:
            g.note(f"{f.name}: {n} dialogue lines")
    return g


def anchor_value(anchor: str) -> int | None:
    a = anchor.strip().upper()
    if a.startswith("FORGE"):
        return None
    m = BC_YEAR.search(a)
    if m:
        return -int(m.group(1))
    m = CE_YEAR.search(a)
    if m:
        return int(m.group(1))
    return "?"  # type: ignore[return-value]


def g5_anchors() -> Gate:
    g = Gate("G5 anchor-order")
    prev: int | None = -10**9
    seen_forge = False
    for f in chapter_files():
        _, fenced = split_prose(f.read_text(encoding="utf-8"))
        first = None
        for b in fenced:  # first NON-EMPTY ◆ STATUS line (blocks open with newline)
            for ln in b.splitlines():
                if "◆" in ln and "STATUS" in ln:
                    first = ln
                    break
            if first:
                break
        if not first:
            g.fail(f"{f.name}: no ◆ STATUS panel fence")
            continue
        m = PANEL_FIRST.search(first)
        if not m:
            g.fail(f"{f.name}: panel first line unparseable: {first[:70]!r}")
            continue
        v = anchor_value(m.group(2))
        if v == "?":
            g.fail(f"{f.name}: anchor unparseable: {m.group(2)[:50]!r}")
        elif v is None:
            if seen_forge or f != chapter_files()[0]:
                g.fail(f"{f.name}: FORGE anchor allowed first-chapter-only")
            seen_forge = True
            g.note(f"{f.name}: FORGE anchor (first only) OK")
        else:
            if v < prev:
                g.fail(f"{f.name}: anchor {v} goes backward (prev {prev})")
            elif v == prev:
                # Equal anchors (transit ~ arrival) are CORRECT order, not overlap.
                # Kit lesson: fix scope, not docs. Span-contiguity needs start-end panels.
                g.note(f"{f.name}: anchor {v} (same-era sequence, allowed)")
            else:
                g.note(f"{f.name}: anchor {v} OK")
            prev = v
    if g.ok():
        g.note("LIMIT: single-anchor order only; span-contiguity needs start-end panels")
    return g


def g6_placeholders() -> Gate:
    g = Gate("G6 placeholders")
    for f in chapter_files():
        s = f.read_text(encoding="utf-8")
        for i, ln in enumerate(s.splitlines(), 1):
            m = PLACEHOLDER.search(ln)
            if m:
                g.fail(f"{f.name}:{i}: {m.group(0)!r}")
    if g.ok():
        g.note(f"{len(chapter_files())} chapters, 0 placeholders (foundation TBDs out of scope)")
    return g


def g7_markers() -> Gate:
    g = Gate("G7 marker-discipline")
    for f in chapter_files():
        s = f.read_text(encoding="utf-8")
        prose, fenced = split_prose(s)
        if "◆" in prose:
            g.fail(f"{f.name}: ◆ in prose")
        cards = [b for b in fenced if b.lstrip().startswith("◆ END OF")]
        others = [b for b in fenced if "◆" in b and not b.lstrip().startswith("◆")]
        if others:
            g.fail(f"{f.name}: ◆ outside panel/card fence")
        if len(cards) > 1:
            g.fail(f"{f.name}: {len(cards)} END OF cards (>1)")
        if cards and not s.rstrip().endswith("```"):
            g.fail(f"{f.name}: END OF card not last")
    if g.ok():
        g.note("markers fenced only; cards ≤1 and last")
    return g


def m1_manifest() -> Gate:
    g = Gate("M1 manifest-edge")
    if not MANIFEST.exists():
        g.fail("manifest missing")
        return g
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    want = man.get("latest_fic_file", "")
    if not (ROOT / want).exists():
        g.fail(f"manifest latest_fic_file missing: {want}")
    n = len(chapter_files())
    if man.get("latest_fic_chapter") != n:
        g.fail(f"manifest latest={man.get('latest_fic_chapter')} vs {n} chapters on disk")
    if g.ok():
        g.note(f"edge ch{man.get('latest_fic_chapter')} matches {n} chapter files")
    return g


def m2_future() -> Gate:
    g = Gate("M2 forbidden-future")
    for f in chapter_files():
        prose, _ = split_prose(f.read_text(encoding="utf-8"))
        for term in FUTURE_DENY:
            if term in prose:
                g.fail(f"{f.name}: forbidden-future term {term!r} in prose")
    if g.ok():
        g.note(f"denylist {FUTURE_DENY} absent from prose")
    return g


def run_all(root: Path | None = None) -> tuple[list[Gate], bool]:
    global ROOT, CHAPTERS, MANIFEST
    if root is not None:
        ROOT, CHAPTERS, MANIFEST = root, root / "chapters", root / "foundation" / "CURRENT_STATE_MANIFEST.json"
    gates = [g1_unreadable(), g2_backslash_n(), g3_digits(), g4_dialogue(),
             g5_anchors(), g6_placeholders(), g7_markers(), m1_manifest(), m2_future()]
    return gates, all(x.ok() for x in gates)


CLEAN_CHAPTER = """# Chapter One — Clean

```
◆ STATUS — Chapter One: FORGE (pre-Earth)
KIND      : test
```

He woke to falling that was not falling.

"I am here," she said.

"Then we begin," he said.

"And we do not stop," she said.
"""


def selftest() -> bool:
    """Kit 09 §3b: every gate must catch its defect; clean must pass."""
    print("SELFTEST: 8 defect fixtures + 1 clean (each gate must fire exactly)")
    cases = {
        "G1": ("bad \u4e2d char", CLEAN_CHAPTER + "\n\u4e2d\n"),
        "G2": ("backslash-n", CLEAN_CHAPTER + "\nX" + BACKSLASH_N + "Y\n"),
        "G3": ("digit", CLEAN_CHAPTER + "\nHe counted 7 stones.\n"),
        "G4": ("no-dialogue", "# T\n\n```\n◆ STATUS — Chapter T: FORGE\nKIND : t\n```\n\nNo speech here at all.\n"),
        "G6": ("placeholder", CLEAN_CHAPTER + "\nName TBD later.\n"),
        "G7": ("marker-in-prose", CLEAN_CHAPTER + "\nA ◆ loose in prose.\n"),
        "M2": ("future-term", CLEAN_CHAPTER + "\nThe Chitauri came.\n"),
        "M1": ("edge-mismatch", None),  # manifest latest=9 vs 1 chapter
    }
    allok = True
    for name, (_, body) in cases.items():
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            (r / "chapters").mkdir()
            (r / "foundation").mkdir()
            (r / "chapters" / "Chapter_01_X.md").write_text(
                body if body is not None else CLEAN_CHAPTER, encoding="utf-8")
            man = {"latest_fic_chapter": 9 if name == "M1" else 1,
                   "latest_fic_file": "chapters/Chapter_01_X.md"}
            (r / "foundation" / "CURRENT_STATE_MANIFEST.json").write_text(
                json.dumps(man), encoding="utf-8")
            gates, _ = run_all(r)
            target = {"G1": 0, "G2": 1, "G3": 2, "G4": 3, "G6": 5, "G7": 6, "M1": 7, "M2": 8}[name]
            fired = [i for i, x in enumerate(gates) if not x.ok()]
            ok = fired == [target]
            print(f"  {name}: {'FIRES-EXACTLY' if ok else 'WRONG got ' + str(fired)}")
            allok = allok and ok
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / "chapters").mkdir()
        (r / "foundation").mkdir()
        (r / "chapters" / "Chapter_01_X.md").write_text(CLEAN_CHAPTER, encoding="utf-8")
        (r / "foundation" / "CURRENT_STATE_MANIFEST.json").write_text(
            json.dumps({"latest_fic_chapter": 1,
                        "latest_fic_file": "chapters/Chapter_01_X.md"}), encoding="utf-8")
        gates, passed = run_all(r)
        print(f"  CLEAN: {'PASSES' if passed else 'FALSE-POSITIVE ' + str([x.name for x in gates if not x.ok()])}")
        allok = allok and passed
    print("SELFTEST:", "PASS" if allok else "FAIL")
    return allok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return 0 if selftest() else 1
    gates, passed = run_all()
    fails = sum(len(x.fails) for x in gates)
    for x in gates:
        print(f"[{'PASS' if x.ok() else 'FAIL'}] {x.name}")
        for m in x.info:
            print(f"         · {m}")
        for m in x.fails:
            print(f"         ✗ {m}")
    print(f"TOTAL: {'PASS' if passed else 'FAIL'} — {fails} failures")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
