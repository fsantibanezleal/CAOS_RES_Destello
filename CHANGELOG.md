# Changelog

All notable changes, newest first, grouped Added / Changed / Fixed / Removed. Versions are `X.XX.XXX` (the `VERSION`
file, the tags and this log); manifests carry the semantic form.

## [0.01.000] - 2026-09-24

### Added

- The renderer (`data-pipeline/rays.py`, `scene.py`): analytic ray casting on spheres, ellipsoids, planes and the
  inside of panoramic cylinders; each ommatidium's luminance integrated over its Gaussian acceptance with 19 rays;
  the exact truth per ommatidium and frame: depth, object, optic flow and time to contact. Checked against closed
  forms (yaw flow, a looming sphere's time to contact and angular size, sphere and plane depths).
- The 13 cases and their 222 stimuli (`data-pipeline/cases.py`): gratings, moving edges, flashes, looming and
  receding discs, wall approach, yaw rotation, corridor, small target, figure over ground, rival fly, natural
  flights, dark and static; directional stimuli mirror-symmetric on the two eyes; seeded textures scaled to the
  eye's resolution; splits by scene layout.
- The dataset stage (`data-pipeline/run.py dataset`, `render_cases.py`): every stimulus rendered for both MaleCNS
  eyes and for flyvis's lattices (engine E3's input), written in the compiled format with an index.
- Wiki: the renderer's equations, the variants, the splits and a gallery of the 13 scenes.

## [0.00.000] - 2026-09-23

### Added

- The product software design document (`docs/design/SDD.md`), written before any code: problem and non-goals,
  contracts, lanes, the twelve methods with their acceptance criteria, thirteen cases in six categories, the oracle,
  the deploy driver, risks and kill criteria.
- The repository instantiated from the product archetype with its example removed: the dormant backend, the data
  tree, guards for content standards, the CI budget, template residue and the design document, CI on `develop` and
  `main`, setup scripts, and the wiki with real content for what exists.
