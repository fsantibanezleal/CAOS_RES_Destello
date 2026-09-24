# Destello

[![ci](https://github.com/fsantibanezleal/CAOS_RES_Destello/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/fsantibanezleal/CAOS_RES_Destello/actions/workflows/ci.yaml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**The male fruit fly's whole nervous system, working, seen through its two eyes.**

The complete connectome of the male *Drosophila* central nervous system, MaleCNS v1.0 (166,700 neurons in brain and
ventral nerve cord; Berg et al., *Cell* 189:5504-5526, 2026, doi:10.1016/j.cell.2026.08.015; data CC BY 4.0), is
driven through both of its real compound eyes (879 measured columns on the left, 892 on the right). Destello runs it
with the published neuron models and shows the real neurons firing, as real soma positions and real arbors lighting
up, from the photoreceptors through the optic lobes to the descending neurons and the nerve cord, in slow motion with
the biological clock always on screen. A visitor can change the stimulus, stimulate or silence any neuron or cell
type, and change the model, and watch what follows.

The science underneath answers, with null wirings as controls (degree-preserving rewiring, a size-matched random
graph, a sign shuffle): which visual computations and behaviours the measured wiring produces on its own, and whether
depth (motion parallax, time to contact) and fast segmentation (figure against ground) can be read from the real
neurons whose job it is.

## What it is not

Not a digital organism, not a claim about experience, and not a complete behavioural model. The connectome is frozen;
only readouts learn. The fly's body is a readout display animated from descending-neuron activity through mappings
from the literature, labelled as such.

## Status

Version 0.01.000: the design (`docs/design/SDD.md`), the scaffold, and the visual world: an analytic renderer of
what each ommatidium of both eyes sees, with the exact truth (depth, object, optic flow, time to contact), and the
13 cases and 222 stimuli of the product. The simulation engine lives in its own package,
[`flycns`](https://github.com/fsantibanezleal/CAOS_FlyCNS). This README lists capabilities only as they land.

## Layout

| Folder | Role |
|---|---|
| `data-pipeline/` | the offline pipeline, plain scripts run by path (no package of its own) |
| `data/` | raw sources (git-ignored), compact derived artifacts, manifests |
| `frontend/` | the companion web (built on the shared app shell) |
| `app/` | an optional backend, dormant: the product is static |
| `docs/` | the wiki: design, architecture, cases, frameworks, guides |
| `scripts/` | setup scripts and the guards continuous integration runs |

## Documentation

Start at [`docs/README.md`](docs/README.md).

## License

Code: MIT. Connectome data are not redistributed beyond compact derived artifacts; sources keep their licences
(MaleCNS: CC BY 4.0).
