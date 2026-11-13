#!/usr/bin/env python3
"""GTT - Ideas: the old name of the inbox engine. Kept as an alias so nothing that calls it breaks.

The engine is gtt_inbox.py (.gtt/contract/inbox.json); an idea is an IDEA-NNN entry of the inbox. This module only
gives the callers that import it (Sonar) the shape they always had, and runs the old command line:

  gtt_idea.py add | triage | park | drop | list   =   gtt_inbox.py --as-ideas ...

The old contract, ideas.json, stays one version as a read-only alias.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import gtt_inbox          # noqa: E402


def contract():
    return gtt_inbox.legacy_contract()


def rows(c=None, include_closed=True):
    return gtt_inbox.legacy_rows(c, include_closed)


if __name__ == "__main__":
    sys.exit(gtt_inbox.main(["--as-ideas"] + sys.argv[1:]))
