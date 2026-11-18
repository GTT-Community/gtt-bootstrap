#!/usr/bin/env python3
"""GTT - health: the result of each `gtt-validate.sh` check, one file per check in .gtt/local/health/<id>.json
({"title", "status": ok|warn|fail, "detail", "at"}). Derived and disposable: validate writes them, this module only reads.

  gtt_health.py list [--json]

`findings()` gives GOV-VALIDATION for a check that failed, warned or is older than the contract allows."""
import datetime
import glob
import json
import os
import sys

HEALTH_DIR = ".gtt/local/health"
STALE_AFTER_H = 48


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def checks():
    """The checks reported, or None when nobody has run `gtt-validate.sh` here."""
    if not os.path.isdir(HEALTH_DIR):
        return None
    out = []
    for path in sorted(glob.glob(os.path.join(HEALTH_DIR, "*.json"))):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        at = data.get("at") if isinstance(data.get("at"), str) else None
        stale = False
        try:
            then = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            stale = (datetime.datetime.now(datetime.timezone.utc) - then).total_seconds() > STALE_AFTER_H * 3600
        except (TypeError, ValueError):
            pass
        status = str(data.get("status") or "").lower()
        out.append({"id": os.path.basename(path)[:-5], "title": data.get("title"), "status": status if status in ("ok", "warn", "fail") else "unknown",
                    "detail": data.get("detail"), "at": at, "stale": stale, "path": path.replace(os.sep, "/")})
    return out


def findings():
    import gtt_findings as gf
    es = gf.language() == "es"
    out = []
    for c in checks() or []:
        state = {"fail": "failed" if not es else "falló", "warn": "warned" if not es else "avisó"}.get(c["status"])
        if state is None and c["stale"]:
            state = "is out of date" if not es else "está vencido"
        if state:
            out.append(gf.make("GOV-VALIDATION", c["id"], c["path"], "gtt_health", level="WARNING" if c["status"] == "fail" else "NOTICE", check=c["id"], state=state))
    return out


def main(argv):
    if argv[:1] != ["list"]:
        print("usage: gtt_health.py list [--json]", file=sys.stderr)
        return 2
    data = checks()
    if "--json" in argv:
        print(json.dumps({"schema": 1, "kind": "gtt-health", "checks": data}, indent=2, ensure_ascii=False))
    else:
        for c in data or []:
            print(f"{c['status']:7} {c['id']}  {c['detail'] or ''}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1:]))
