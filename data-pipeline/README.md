# data-pipeline

The offline pipeline: plain scripts run by path (`python data-pipeline/run.py <stage>`), in the `.venv-pipeline`
environment. It declares no package; the simulation engine is the separately published `flycns`.

## Stages

Each stage is deterministic and seeded, reads the previous stage's output from disk, and writes its own. Stages land
with the unit that implements them; none exists as an empty body.

| Stage | Responsibility |
|---|---|
| ingest | fetch the MaleCNS release files, skeletons, neuropil meshes, the flyvis ensemble and the other pinned sources, and accept them only on matching hashes |
| preprocess | compile the connectome with `flycns`, build the anatomy levels of detail and the per-eye column tables |
| dataset | render every case and variant for both eyes with exact ground truth; assign train, validation, calibration and test splits by scene layout and seed |
| feature extraction | simulate every engine and null over the case matrix and record the activity |
| train | fit the learned readouts on the train split only |
| infer | run every readout over the held-out cells |
| evaluate | score every method against ground truth and physiology; compare with the nulls |
| export | write the compact web artifacts and their manifest |
| validate | check completeness, hashes and schemas of everything exported |
