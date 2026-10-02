#!/usr/bin/env python3
"""Anonymous artifact export.

Builds an author-anonymous snapshot of the repository for double-blind review:

* copies the tracked files of one commit (``git archive``; no ``.git``, no history),
* optionally adds the GPU-branch areas from another ref (``--gpu-ref``), read-only,
* optionally copies selected untracked ``results/`` paths (``--include-results``),
* replaces every identity string listed in ``tools/anon_targets.json``
  (text files only; binary files that contain a target are reported, never edited),
* optionally renames the Python package ``continuum`` (``--rename-package``),
* re-scans the whole output for every target and for generic leaks
  (``/home/``, e-mail addresses, ``github.com/<owner>``) and exits non-zero on any hit,
* writes ``ANON_MANIFEST.json`` into the output directory.

``--report-only`` scans instead of exporting and writes the occurrence table
(``tools/ANON_TARGETS.md``, ``tools/anon_occurrences.csv``).

Exit codes: 0 clean; 1 error or remaining hit of an applied target / generic check;
2 only targets that still need a user decision (``auto: false`` without ``decision``) remain.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

TOOL_VERSION = "anon-export-1"
GPU_AREAS = ("docs/research/gpu", "experiments/gpu", "results/gpu")
MANIFEST_NAME = "ANON_MANIFEST.json"
SCRIPT_DIR = Path(__file__).resolve().parent


# --------------------------------------------------------------------------- git helpers

def git(repo: Path, *args: str, binary: bool = False):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode()


def repo_root() -> Path:
    return Path(git(SCRIPT_DIR, "rev-parse", "--show-toplevel").strip())


def existing_paths(repo: Path, rev: str, paths) -> list[str]:
    found = []
    for p in paths:
        if git(repo, "ls-tree", "--name-only", rev, "--", p).strip():
            found.append(p)
    return found


@dataclass
class Entry:
    path: str
    data: bytes | None  # None for symlinks
    mode: int = 0o644
    link: str | None = None
    origin: str = "commit"  # commit | gpu-ref | results


def archive_entries(repo: Path, rev: str, paths=(), origin="commit") -> list[Entry]:
    raw = git(repo, "archive", "--format=tar", rev, "--", *paths, binary=True)
    out = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        for m in tf.getmembers():
            if m.isdir() or m.name == "pax_global_header":
                continue
            if m.issym():
                out.append(Entry(m.name, None, m.mode, m.linkname, origin))
            elif m.isfile():
                out.append(Entry(m.name, tf.extractfile(m).read(), m.mode, None, origin))
    return out


# --------------------------------------------------------------------------- targets

@dataclass
class Target:
    id: str
    kind: str
    pattern: str
    regex: bool
    replacement: str
    auto: bool
    scope: str
    note: str
    decision: str | None
    rx: re.Pattern = field(init=False)
    brx: re.Pattern = field(init=False)

    def __post_init__(self):
        src = self.pattern if self.regex else re.escape(self.pattern)
        self.rx = re.compile(src, re.M)
        self.brx = re.compile(src.encode(), re.M)

    @property
    def status(self) -> str:  # apply | keep | undecided
        return self.decision or "undecided"


def load_targets(path: Path, apply_ids, keep_ids):
    doc = json.loads(path.read_text())
    targets = []
    for t in doc["targets"]:
        t = dict(t)
        dec = t.get("decision")
        if t["id"] in apply_ids:
            dec = "apply"
        if t["id"] in keep_ids:
            dec = "keep"
        if t["auto"] and dec is None:
            dec = "apply"
        targets.append(Target(t["id"], t["kind"], t["pattern"], bool(t.get("regex")), t["replacement"],
                              bool(t["auto"]), t.get("scope", "tracked"), t.get("note", ""), dec))
    unknown = (set(apply_ids) | set(keep_ids)) - {t.id for t in targets}
    if unknown:
        sys.exit(f"unknown target id(s): {sorted(unknown)}")
    return doc, targets


# --------------------------------------------------------------------------- content helpers

def as_text(data: bytes) -> str | None:
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def binary_views(data: bytes) -> list[bytes]:
    """Raw bytes plus every zlib stream that decompresses (covers PDF FlateDecode)."""
    views = [data]
    if data[:5] == b"%PDF-":
        for m in re.finditer(rb"stream\r?\n", data):
            end = data.find(b"endstream", m.end())
            if end < 0:
                continue
            try:
                views.append(zlib.decompress(data[m.end():end]))
            except zlib.error:
                pass
    return views


def generic_rx(doc):
    g = doc["generic_checks"]
    return (re.compile(g["home_path"]), re.compile(g["email"]), re.compile(g["github_owner"]),
            set(g.get("github_owner_allow", [])), set(g.get("email_allow", [])))


def generic_hits(text: str, grx) -> list[tuple[str, str]]:
    home, email, gh, gh_allow, mail_allow = grx
    hits = [("generic:home_path", m.group(0)) for m in home.finditer(text)]
    hits += [("generic:email", m.group(0)) for m in email.finditer(text) if m.group(0) not in mail_allow]
    hits += [("generic:github_owner", m.group(0)) for m in gh.finditer(text) if m.group(1) not in gh_allow]
    return hits


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# --------------------------------------------------------------------------- package rename

def rename_package(entries: list[Entry], new: str, report: dict):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", new) or new == "continuum":
        sys.exit(f"--rename-package: invalid name {new!r}")
    subpkgs = sorted({e.path.split("/")[2] for e in entries
                      if e.path.startswith("src/continuum/") and e.path.count("/") >= 3})
    forms = [
        ("src/continuum", re.compile(r"(?<![A-Za-z0-9_])src/continuum(?![A-Za-z0-9_-])"), f"src/{new}"),
        ("from continuum", re.compile(r"\bfrom continuum(?=[\s.])"), f"from {new}"),
        ("import continuum", re.compile(r"\bimport continuum(?=[\s.,]|$)", re.M), f"import {new}"),
    ]
    if subpkgs:
        forms.append(("continuum.<subpackage>",
                      re.compile(r"(?<![A-Za-z0-9_./-])continuum\.(" + "|".join(map(re.escape, subpkgs)) + r")\b"),
                      new + r".\1"))
    pyproject = re.compile(r"""^(\s*name\s*=\s*["'])continuum(["'])""", re.M)
    per_form = collections.Counter()
    per_file = {}
    for e in entries:
        if e.data is None:
            continue
        text = as_text(e.data)
        if text is None:
            continue
        counts = {}
        for name, rx, rep in forms:
            text, n = rx.subn(rep, text)
            if n:
                counts[name] = n
        if e.path.endswith("pyproject.toml"):
            text, n = pyproject.subn(r"\g<1>" + new + r"\2", text)
            if n:
                counts["pyproject name"] = n
        if counts:
            e.data = text.encode("utf-8")
            per_file[e.path] = counts
            per_form.update(counts)
    moved = 0
    for e in entries:
        if e.path.startswith("src/continuum/"):
            e.path = f"src/{new}/" + e.path[len("src/continuum/"):]
            moved += 1
    residual = collections.Counter()
    rx_res = re.compile(r"(?i)\bcontinuum\b")
    for e in entries:
        text = as_text(e.data) if e.data is not None else None
        if text:
            n = len(rx_res.findall(text))
            if n:
                residual[e.path] = n
    report.update({
        "new_name": new,
        "subpackages": subpkgs,
        "files_moved_from_src_continuum": moved,
        "rewrites_by_form": dict(per_form),
        "rewritten_files": per_file,
        "residual_word_continuum_total": sum(residual.values()),
        "residual_word_continuum_top_files": dict(residual.most_common(15)),
        "residual_note": "case-insensitive word 'continuum' left untouched: prose, the cited Continuum paper, "
                         "legacy repo name vllm-continuum, schema string continuum-observation-v1, "
                         "legacy kv_transfer_params keys continuum.arm/continuum.keep",
    })


# --------------------------------------------------------------------------- export

def check_out_dir(out: Path, repo: Path):
    out = out.resolve()
    if out == repo or repo in out.parents:
        sys.exit(f"--out must be outside the repository: {out}")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        sys.exit(f"--out exists and is not an empty directory: {out}")
    return out


def read_results_list(repo: Path, list_file: Path, present: set[str]) -> tuple[list[Entry], list[str]]:
    entries, notes = [], []
    for raw in list_file.read_text().splitlines():
        rel = raw.split("#", 1)[0].strip().rstrip("/")
        if not rel:
            continue
        p = (repo / rel).resolve()
        if repo / "results" not in p.parents and p != repo / "results":
            sys.exit(f"--include-results: path outside results/: {rel}")
        if not p.exists():
            sys.exit(f"--include-results: missing path: {rel}")
        files = [p] if p.is_file() or p.is_symlink() else sorted(
            Path(d) / f for d, _, fs in os.walk(p) for f in fs)
        for f in files:
            r = str(f.relative_to(repo))
            if r in present:
                notes.append(f"already tracked, skipped: {r}")
                continue
            present.add(r)
            if f.is_symlink():
                entries.append(Entry(r, None, 0o777, os.readlink(f), "results"))
            else:
                entries.append(Entry(r, f.read_bytes(), f.stat().st_mode & 0o777, None, "results"))
    return entries, notes


def anonymize(entries: list[Entry], targets: list[Target]):
    applied = [t for t in targets if t.status == "apply"]
    replaced = collections.Counter()
    replaced_files = collections.Counter()
    binary_with_targets = {}
    hash_bearing = []
    for e in entries:
        new_path = e.path
        for t in applied:
            new_path, n = t.rx.subn(t.replacement, new_path)
            if n:
                replaced[t.id] += n
        e.path = new_path
        if e.data is None:
            for t in applied:
                e.link, n = t.rx.subn(t.replacement, e.link)
                if n:
                    replaced[t.id] += n
            continue
        text = as_text(e.data)
        if text is None:
            hits = sorted({t.id for t in targets for v in binary_views(e.data) if t.brx.search(v)})
            if hits:
                binary_with_targets[e.path] = hits
            continue
        changed = False
        for t in applied:
            text, n = t.rx.subn(t.replacement, text)
            if n:
                replaced[t.id] += n
                replaced_files[t.id] += 1
                changed = True
        if changed:
            if "sha256" in e.data.decode("utf-8", "replace") or "/plans/" in e.path:
                hash_bearing.append(e.path)
            e.data = text.encode("utf-8")
    return replaced, replaced_files, binary_with_targets, hash_bearing


def write_entries(out: Path, entries: list[Entry]):
    seen = set()
    for e in entries:
        if e.path in seen:
            sys.exit(f"path collision after anonymization: {e.path}")
        seen.add(e.path)
        dst = out / e.path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if e.data is None:
            os.symlink(e.link, dst)
        else:
            dst.write_bytes(e.data)
            os.chmod(dst, 0o755 if e.mode & 0o111 else 0o644)


def scan_tree(out: Path, targets: list[Target], grx, skip=(MANIFEST_NAME,)):
    """Return {category: [(path, line, target_id, match)]} for everything left in ``out``."""
    res = collections.defaultdict(list)
    cat = {"apply": "remaining_applied", "undecided": "remaining_undecided", "keep": "kept"}
    for d, dirs, files in os.walk(out):
        for name in dirs + files:
            rel = str((Path(d) / name).relative_to(out))
            for t in targets:
                if t.rx.search(rel):
                    res[cat[t.status]].append((rel, 0, t.id, "<path name>"))
            for gid, m in generic_hits(rel, grx):
                res["remaining_generic"].append((rel, 0, gid, m))
        for name in files:
            p = Path(d) / name
            rel = str(p.relative_to(out))
            if rel in skip:
                continue
            if p.is_symlink():
                text = os.readlink(p)
            else:
                data = p.read_bytes()
                text = as_text(data)
                if text is None:
                    for t in targets:
                        if any(t.brx.search(v) for v in binary_views(data)):
                            res["binary_" + cat[t.status]].append((rel, 0, t.id, "<binary>"))
                    continue
            for t in targets:
                for m in t.rx.finditer(text):
                    res[cat[t.status]].append((rel, line_of(text, m.start()), t.id, m.group(0)[:80]))
            for gid, m in generic_hits(text, grx):
                res["remaining_generic"].append((rel, 0, gid, m[:80]))
    return res


def summarize(hits):
    return {k: {"count": len(v), "by_target": dict(collections.Counter(h[2] for h in v)),
                "first": [f"{h[0]}:{h[1]} [{h[2]}]" for h in v[:30]]}
            for k, v in sorted(hits.items())}


def do_export(a, repo: Path):
    out = check_out_dir(Path(a.out), repo)
    doc, targets = load_targets(Path(a.targets), set(a.apply), set(a.keep))
    grx = generic_rx(doc)
    for t in targets:  # a replacement must not re-introduce a leak
        bad = [u.id for u in targets if u.status == "apply" and u.rx.search(t.replacement)]
        if bad or generic_hits(t.replacement, grx):
            sys.exit(f"replacement of {t.id} matches {bad or 'a generic check'}: {t.replacement!r}")
    excl = doc.get("export_exclude", []) + list(a.exclude)
    commit = git(repo, "rev-parse", "--verify", a.commit + "^{commit}").strip()

    def excluded(p):
        return any(p == x.rstrip("/") or p.startswith(x.rstrip("/") + "/") for x in excl)

    entries = [e for e in archive_entries(repo, commit) if not excluded(e.path)]
    notes = []
    gpu = None
    if a.gpu_ref:
        gcommit = git(repo, "rev-parse", "--verify", a.gpu_ref + "^{commit}").strip()
        areas = existing_paths(repo, gcommit, GPU_AREAS)
        present = {e.path for e in entries}
        added, conflicts = 0, []
        for e in archive_entries(repo, gcommit, areas, "gpu-ref") if areas else []:
            if excluded(e.path):
                continue
            if e.path in present:
                conflicts.append(e.path)
                continue
            entries.append(e)
            added += 1
        gpu = {"ref": a.gpu_ref, "commit": gcommit, "areas_found": areas,
               "areas_missing": [x for x in GPU_AREAS if x not in areas],
               "files_added": added, "conflicts_kept_commit_version": conflicts}
    if a.include_results:
        res_entries, rnotes = read_results_list(repo, Path(a.include_results), {e.path for e in entries})
        entries += [e for e in res_entries if not excluded(e.path)]
        notes += rnotes

    replaced, replaced_files, binaries, hash_bearing = anonymize(entries, targets)
    rename = {}
    if a.rename_package:
        rename_package(entries, a.rename_package, rename)
    write_entries(out, entries)

    hits = scan_tree(out, targets, grx)
    failing = len(hits.get("remaining_applied", [])) + len(hits.get("remaining_generic", [])) \
        + len(hits.get("binary_remaining_applied", []))
    undecided = len(hits.get("remaining_undecided", [])) + len(hits.get("binary_remaining_undecided", []))
    status = "FAIL" if failing else ("NEEDS_DECISION" if undecided else "PASS")

    manifest = {
        "tool": TOOL_VERSION,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "git_history_included": False,
        "options": {"commit": a.commit, "gpu_ref": a.gpu_ref, "rename_package": a.rename_package,
                    "include_results": Path(a.include_results).name if a.include_results else None,
                    "apply": sorted(a.apply), "keep": sorted(a.keep), "exclude": excl},
        "gpu": gpu,
        "files": dict(collections.Counter(e.origin for e in entries)),
        "targets": {t.id: {"kind": t.kind, "status": t.status, "replaced": replaced.get(t.id, 0),
                           "files": replaced_files.get(t.id, 0)} for t in targets},
        "replaced_total": sum(replaced.values()),
        "binary_files_with_targets_unmodified": binaries,
        "modified_hash_bearing_files": sorted(hash_bearing),
        "rename_package": rename or None,
        "notes": notes,
        "check": {"status": status, **summarize(hits)},
    }
    mtext = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    for t in targets:  # the manifest must itself be clean
        if t.status == "apply" and t.rx.search(mtext):
            mtext = t.rx.sub(t.replacement, mtext)
    if generic_hits(mtext, grx):
        print("warning: manifest contains generic-pattern strings", file=sys.stderr)
    (out / MANIFEST_NAME).write_text(mtext)

    print(f"export: {len(entries)} files -> {out}")
    print(f"commit {commit[:12]}" + (f", gpu-ref {gpu['commit'][:12]} (+{gpu['files_added']})" if gpu else ""))
    print(f"replaced: {sum(replaced.values())} occurrences over {len(replaced)} targets")
    for tid, n in replaced.most_common():
        print(f"  {tid:28s} {n}")
    if rename:
        print(f"rename-package -> {rename['new_name']}: {rename['rewrites_by_form']}, "
              f"{len(rename['rewritten_files'])} files rewritten, {rename['files_moved_from_src_continuum']} moved")
    if binaries:
        print(f"binary files containing targets (not modified): {binaries}")
    if hash_bearing:
        print(f"modified hash-bearing files: {len(hash_bearing)}")
    for k, v in sorted(hits.items()):
        print(f"{k}: {len(v)}")
        for h in v[:15]:
            print(f"  {h[0]}:{h[1]} [{h[2]}] {h[3]}")
    print(f"check: {status}")
    return 1 if failing else (2 if undecided else 0)


# --------------------------------------------------------------------------- report

def scan_entries_lines(entries: list[Entry], targets: list[Target], source: str, rows: list):
    for e in entries:
        if e.data is None:
            continue
        text = as_text(e.data)
        for t in targets:
            if t.rx.search(e.path):
                rows.append((t.id, source, e.path, 0, 1, "<path name>"))
        if text is None:
            for t in targets:
                n = sum(len(t.brx.findall(v)) for v in binary_views(e.data))
                if n:
                    rows.append((t.id, source, e.path, 0, n, "<binary>"))
            continue
        lines = None
        for t in targets:
            for m in t.rx.finditer(text):
                lines = lines if lines is not None else text.split("\n")
                ln = line_of(text, m.start())
                rows.append((t.id, source, e.path, ln, 1, lines[ln - 1].strip()[:160].rstrip()))


def scan_results_counts(repo: Path, targets: list[Target], rows: list):
    tracked = set(git(repo, "ls-files", "results").splitlines())
    for d, _, files in os.walk(repo / "results"):
        for name in files:
            p = Path(d) / name
            rel = str(p.relative_to(repo))
            if rel in tracked or p.is_symlink():
                continue
            data = p.read_bytes()
            text = as_text(data)
            for t in targets:
                n = len(t.rx.findall(rel))
                if text is not None:
                    n += len(t.rx.findall(text))
                else:
                    n += sum(len(t.brx.findall(v)) for v in binary_views(data))
                if n:
                    rows.append((t.id, "results", rel, 0, n, ""))


def md_cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def do_report(a, repo: Path):
    doc, targets = load_targets(Path(a.targets), set(a.apply), set(a.keep))
    commit = git(repo, "rev-parse", "--verify", a.commit + "^{commit}").strip()
    excl = doc.get("export_exclude", [])
    entries = [e for e in archive_entries(repo, commit)
               if not any(e.path == x.rstrip("/") or e.path.startswith(x.rstrip("/") + "/") for x in excl)]
    rows: list = []
    scan_entries_lines(entries, targets, "main", rows)
    gcommit = None
    if a.gpu_ref:
        gcommit = git(repo, "rev-parse", "--verify", a.gpu_ref + "^{commit}").strip()
        areas = existing_paths(repo, gcommit, GPU_AREAS)
        if areas:
            scan_entries_lines(archive_entries(repo, gcommit, areas, "gpu-ref"), targets, "gpu", rows)
    if a.report_results:
        scan_results_counts(repo, targets, rows)

    out_dir = Path(a.report_dir)
    with (out_dir / "anon_occurrences.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["target_id", "source", "path", "line", "count", "excerpt"])
        w.writerows(rows)

    cnt = collections.defaultdict(collections.Counter)
    for tid, src, _p, _l, n, _x in rows:
        cnt[tid][src] += n
    by_kind = collections.defaultdict(lambda: collections.Counter())
    for t in targets:
        k = by_kind[t.kind]
        k["targets"] += 1
        k["auto"] += t.auto
        k["needs_decision"] += not t.auto
        for src in ("main", "gpu", "results"):
            k[src] += cnt[t.id][src]

    when = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    L = ["# Anonymization targets", "",
         f"Generated by `tools/anon_export.py --report-only` at {when}.",
         f"Sources: `main` = tracked files of `{a.commit}` ({commit[:12]})"
         + (f"; `gpu` = `{a.gpu_ref}` ({gcommit[:12]}) under {', '.join(GPU_AREAS)}" if gcommit else "")
         + ("; `results` = untracked files under `results/` (counts only, no line numbers)"
            if a.report_results else "") + ".",
         "Definitions: `tools/anon_targets.json`. Full location list: `tools/anon_occurrences.csv`.",
         "This file, the JSON and the CSV are excluded from the export.",
         "Counts are per pattern on the original text. Patterns overlap (for example "
         "`/home/rebel/continuum-npu` also matches `path-npu-home` and `name-old-repo`), so column sums "
         "overstate distinct strings; the export applies entries top to bottom and the first match wins.",
         "auto = yes: replaced by default. auto = **no**: needs a user decision (`decision` in the JSON, "
         "or `--apply ID` / `--keep ID`).", "",
         "## Counts by kind", "",
         "| kind | targets | auto | needs decision | occurrences main | occurrences gpu | occurrences results |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    for kind in sorted(by_kind):
        k = by_kind[kind]
        L.append(f"| {kind} | {k['targets']} | {k['auto']} | {k['needs_decision']} | {k['main']} | {k['gpu']} | "
                 f"{k['results']} |")
    tot = collections.Counter()
    for k in by_kind.values():
        tot.update(k)
    L.append(f"| **total** | {tot['targets']} | {tot['auto']} | {tot['needs_decision']} | {tot['main']} | "
             f"{tot['gpu']} | {tot['results']} |")
    L += ["", "## Targets", "",
          "| id | kind | pattern | regex | replacement | auto | scope | main | gpu | results | note |",
          "|---|---|---|---|---|---|---|---:|---:|---:|---|"]
    for t in targets:
        c = cnt[t.id]
        L.append(f"| `{t.id}` | {t.kind} | `{md_cell(t.pattern)}` | {'yes' if t.regex else ''} | "
                 f"`{md_cell(t.replacement)}` | {'yes' if t.auto else '**no**'} | {t.scope} | {c['main']} | "
                 f"{c['gpu']} | {c['results']} | {md_cell(t.note)} |")
    L += ["", f"## Locations (first {a.cap} per target; main and gpu)", ""]
    for t in targets:
        locs = [r for r in rows if r[0] == t.id and r[1] in ("main", "gpu")]
        res_files = [r for r in rows if r[0] == t.id and r[1] == "results"]
        if not locs and not res_files:
            continue
        L.append(f"### `{t.id}` ({t.kind})")
        L.append("")
        if locs:
            L.append(f"{sum(r[4] for r in locs)} occurrences in {len({(r[1], r[2]) for r in locs})} files.")
            L.append("")
            for r in locs[:a.cap]:
                L.append(f"- {r[1]}: `{r[2]}:{r[3]}`")
            if len(locs) > a.cap:
                L.append(f"- ... {len(locs) - a.cap} more in the CSV")
            L.append("")
        if res_files:
            top = sorted(res_files, key=lambda r: -r[4])[:5]
            L.append(f"results: {sum(r[4] for r in res_files)} occurrences in {len(res_files)} files; largest: "
                     + ", ".join(f"`{r[2]}` ({r[4]})" for r in top))
            L.append("")
    (out_dir / "ANON_TARGETS.md").write_text("\n".join(L).rstrip("\n") + "\n")
    print(f"report: {len(rows)} rows -> {out_dir}/ANON_TARGETS.md, anon_occurrences.csv")
    return 0


# --------------------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--commit", default="HEAD", help="commit whose tracked files are exported (default HEAD)")
    p.add_argument("--out", help="output dir; must not exist or be empty, and must be outside the repository")
    p.add_argument("--gpu-ref", help="also add tracked files under " + ", ".join(GPU_AREAS) + " from this ref")
    p.add_argument("--rename-package", metavar="NEWNAME", help="rename Python package continuum (default: off)")
    p.add_argument("--include-results", metavar="LIST_FILE",
                   help="file with one results/ path per line (file or dir) to copy from the working tree")
    p.add_argument("--targets", default=str(SCRIPT_DIR / "anon_targets.json"))
    p.add_argument("--apply", action="append", default=[], metavar="ID", help="apply an auto=false target")
    p.add_argument("--keep", action="append", default=[], metavar="ID", help="accept an auto=false target as is")
    p.add_argument("--exclude", action="append", default=[], metavar="PATH", help="extra path prefix to exclude")
    p.add_argument("--report-only", action="store_true", help="write ANON_TARGETS.md + anon_occurrences.csv")
    p.add_argument("--report-dir", default=str(SCRIPT_DIR))
    p.add_argument("--report-results", action="store_true", help="report mode: also count hits in results/")
    p.add_argument("--cap", type=int, default=20, help="report mode: locations listed per target")
    a = p.parse_args(argv)
    repo = repo_root()
    if a.report_only:
        return do_report(a, repo)
    if not a.out:
        p.error("--out is required")
    return do_export(a, repo)


if __name__ == "__main__":
    sys.exit(main())
