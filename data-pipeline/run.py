#!/usr/bin/env python3
"""Run a pipeline stage by name: ``python data-pipeline/run.py <stage> [options]``.

Paths default to the local data vault (``DESTELLO_DATA``, default ``E:/_Datos/destello``): the compiled MaleCNS and
its eye geometry under ``compiled/``, the flyvis extraction under ``models/flyvis-1.2.0``, rendered cases under
``cases/``. Every stage is deterministic and seeded, reads the previous stage's output and writes its own; a stage run
again keeps what is already on disk.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DATA = Path(os.environ.get("DESTELLO_DATA", "E:/_Datos/destello"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=["dataset"])
    parser.add_argument("--cases", nargs="*", default=None, help="only these cases (C01 ... C13)")
    args = parser.parse_args()
    if args.stage == "dataset":
        import render_cases

        index = render_cases.run(DATA / "compiled" / "malecns-v1.0", DATA / "compiled" / "malecns-v1.0-eyes-geometry.json",
                                 DATA / "models" / "flyvis-1.2.0" / "lattice-000", DATA / "cases", args.cases)
        print(f"dataset: {len(index)} stimuli indexed in {DATA / 'cases'}")


if __name__ == "__main__":
    main()
