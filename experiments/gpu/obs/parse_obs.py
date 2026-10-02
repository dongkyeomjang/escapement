"""Parse the GTASK03 observation-patch lines out of a vLLM server log.

``[GSTEP]`` — one line per executed (non-dummy) model step, v2 runner dispatch.
``[GPFX]``  — LOOKUP / ALLOC / ALLOC_FAIL, one line each per WAITING-request
admission attempt (scheduler). Lines keep log order, which is execution order
within the single EngineCore process.
"""

from __future__ import annotations

from pathlib import Path
import re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_KV = re.compile(r"(\w+)=(\S+)")


def _num(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return None if v == "None" else v


def parse(log_path: Path) -> list[dict]:
    out = []
    for i, raw in enumerate(Path(log_path).read_text(errors="replace").splitlines()):
        line = _ANSI.sub("", raw)
        if "[GSTEP]" in line:
            body = line.split("[GSTEP]", 1)[1]
            rec = {"kind": "STEP"}
        elif "[GPFX]" in line:
            body = line.split("[GPFX]", 1)[1].strip()
            op, body = body.split(" ", 1)
            rec = {"kind": op}
        else:
            continue
        rec.update({k: _num(v) for k, v in _KV.findall(body)})
        rec["line"] = i
        out.append(rec)
    return out
