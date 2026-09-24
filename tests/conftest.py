"""The pipeline is plain scripts run by path, not a package: the tests import its modules the same way."""

import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1] / "data-pipeline"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))
