# Setup: two environments, the tests, the guards

Destello uses two Python environments:

| Environment | File | Purpose |
|---|---|---|
| `.venv` | `requirements.txt` and `requirements-dev.txt` | the tests and the guards; light |
| `.venv-pipeline` | `requirements-precompute.txt` (and `requirements-gpu.txt`) | the offline pipeline and its engines; local only |

```bash
bash scripts/setup.sh          # or, in PowerShell: .\scripts\setup.ps1
.venv/Scripts/python -m pytest -rs
```

Guards (standard library only; continuous integration runs them first):

```bash
python scripts/check_content_standards.py   # no em-dash, no emoji in tracked text
python scripts/check_ci_budget.py           # workflows stay cheap and trunk-only
python scripts/check_template_residue.py    # nothing of the archetype's example survives
python scripts/check_sdd.py                 # every requirement names a gate that exists
```

The heavy sources (the MaleCNS release files, skeletons, meshes, model weights) are downloaded by the pipeline's
ingest stage into the data vault outside the repository, never into git.
