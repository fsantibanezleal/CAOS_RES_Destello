# Destello · software design document (product)

Written 2026-09-23, after the research and the plan and before any scaffolding. It is the review target for the
design; code follows it. Each non-trivial unit adds a feature design under `docs/design/features/<slug>/`
(requirements in EARS, design, tasks) before its code, and every requirement names the gate that verifies it.

## 1. Problem

The male fruit fly's complete central nervous system has been mapped neuron by neuron: MaleCNS v1.0, 166,700 neurons
in brain and ventral nerve cord, 11,710 cell types (Berg et al., *Cell* 189:5504-5526, 2026,
doi:10.1016/j.cell.2026.08.015, data CC BY 4.0). Both of its optic lobes are mapped column by column: 879 columns on
the left, 892 on the right, each with its lamina, R7 and R8 neurons.

Destello answers three questions, and shows the answer happening:

1. **What does the measured wiring do when the fly's own two eyes feed it?** Drive the real photoreceptors of both
   eyes with a visual scene, run the whole CNS under the published neuron models, and watch the real neurons fire,
   from the retina through the lamina, medulla, lobula and lobula plate, into the visual projection neurons, the
   central brain, the descending neurons and the nerve cord.
2. **Which visual computations and behaviours come from the wiring itself?** Measure direction selectivity, looming
   selectivity, the giant-fibre escape, optomotor responses and object responses on the real wiring, and on the same
   wiring degree-preservingly rewired, replaced by a size-matched random graph, and with its signs shuffled.
3. **Can depth and fast segmentation be read from the real neurons whose job it is?** Depth as the fly measures it
   (motion parallax, time to contact) and segmentation as the fly does it (figure against ground by relative motion),
   read from T4/T5, LPLC2, LC4 and the lobula plate, compared with classical computer vision on the same eye input,
   with learned readouts, and with a monocular depth foundation model given a full-resolution view, all against exact
   ground truth.

## 2. Non-goals

- Not a digital organism, not a claim about experience or consciousness, and not a complete behavioural model. The
  measured wiring alone is known NOT to form a heading bump, to turn toward objects, or to track small objects under
  these neuron models (reported by flyverse's audits); Destello shows those as open, with the named reason, rather
  than scripting them.
- The connectome is frozen. No synapse count or sign is trained. Only readouts (V6, V7) learn.
- Not real time. Whole-CNS simulation runs at a fraction of real time; the presentation is slow motion with the
  biological clock on screen.
- The body is a readout display: a kinematic fly animated from descending-neuron activity through mappings taken
  from the literature, labelled as such. No physics body, no claim that the brain controls muscles.
- MaleCNS only in this product. FlyWire (female, brain only, no histamine) and BANC are out of scope; the engine
  package is written so another release can be added later.
- Not a replacement for research simulators (Brian2, NEST, GeNN). The reference engine is checked against a literal
  Brian2 transcription; it does not claim more.

## 3. Components

| Component | Where | Role |
|---|---|---|
| `flycns` (Python) | separate repository `CAOS_FlyCNS`, published on PyPI | compiles MaleCNS into a signed graph with positions and per-eye columns; eye model; graded and spiking dynamics; recorder |
| `@fasl-work/flycns` (TypeScript/WGSL) | same repository, published on npm | the same dynamics in the browser (WebGPU compute, WASM fallback), loaders for the compiled graph |
| pipeline | `data-pipeline/` here, plain scripts run by path | ingest, preprocess, cases and splits, simulate, readouts, train, infer, evaluate, export, validate |
| web | `frontend/` here | six pages on the shared shell; the App workbench; the focus route; the architecture modal |
| wiki | `docs/` here | theory, equations, references, diagrams, guides, the data contract |

## 4. Contracts

### 4.1 Ingestion (raw to pipeline)

| Source | Form | Checks | Outlier policy |
|---|---|---|---|
| MaleCNS v1.0 annotations, transmitters, weights | official feathers from `storage.googleapis.com/flyem-male-cns/v1.0/` | SHA-256 locked; required columns present; body IDs unique; weights non-negative integers | a file whose hash differs is rejected, never used |
| MaleCNS skeletons | SWC per body ID | parent links form a tree; coordinates inside the CNS bounding box | a malformed skeleton is dropped and counted; the neuron keeps its soma |
| MaleCNS neuropil meshes | neuroglancer precomputed legacy meshes (brain 90 ROIs, VNC 27) | fragment counts, finite vertices | a broken fragment is dropped and counted |
| flyvis ensemble | the published 50-model ensemble, pinned revision | checksum, parameter shapes | mismatch rejected |
| Fly body | flybody meshes (Apache-2.0), pinned commit | vertex and face counts | mismatch rejected |
| Depth Anything V2 small | pinned weights (Apache-2.0) | checksum | mismatch rejected |
| Visitor input (live lane) | a stimulus specification (JSON) or a video/webcam stream | schema, units and ranges; frame size, rate and duration limits; luminance normalised to [0, 1] | out-of-range values rejected with the failing field and range named; blank or NaN frames rejected |

### 4.2 Artifact (pipeline to web)

A top-level manifest indexes every artifact with its schema version, byte size and SHA-256; the browser verifies
each file before use and stops on a mismatch (it never substitutes other data). A TypeScript mirror of the manifest
types fails the web build on drift.

| Artifact | Content |
|---|---|
| graph | the live engine's neuron table and signed synapse CSR, sharded under 50 MB per file |
| anatomy | somas (quantised positions, class, type, side), simplified arbors per neuropil shard, full arbors per pathway on demand, neuropil meshes, the fly body |
| eyes | per-eye column tables: hex coordinates, modelled viewing directions, photoreceptor and lamina body IDs, pale/yellow/DRA type |
| cases | per case and variant: the stimulus, each eye's input, recordings per engine (spikes by tick, graded activity quantised per frame), readout maps, ground truth, metrics |
| benchmark | the method x case x variant metric matrix, the validation ledger, the null comparisons |

## 5. Lanes

| Lane | What runs there | Basis |
|---|---|---|
| Offline (canonical) | every engine E1-E4 and nulls N1-N3 over the whole case matrix; every readout; training; V8 | whole-CNS simulation of one second at 0.1 ms steps is minutes of GPU per run; the matrix is thousands of runs |
| Replay (web default) | recordings of every case and variant for the default engine, and selected others | measured at export; the first paint never waits for a simulation |
| Live (web) | the browser engine (the default engine and E2) on WebGPU or WASM; readouts V1, V3, V4, V5, V6; V7 through onnxruntime-web if its parity gate passes; visitor stimuli and video; closed loop for the yaw and loom cases | accepted only when parity with the offline engine and the measured speed floor (section 9) pass; otherwise the tab says replay only |

## 6. Methods and their acceptance criteria

Each method is implemented only when its unit carries the engine, pinned dependencies and provenance, configuration,
training or calibration where it applies, checkpoints, inference in the shared result schema over every held-out
cell, evaluation, exported artifacts, tests and documentation.

| Id | Method | Accepted when |
|---|---|---|
| E1 | The published LIF (Shiu et al. 2024) on every neuron | constants equal the published `model.py`; a literal Brian2 transcription matches spike for spike on the parity circuits; every matrix cell simulated and reported, whatever the optic lobe does |
| E2 | Graded optic lobe, flyvis type parameters on the real neuron-level wiring of both eyes; LIF elsewhere | activity bounded on every cell (no divergence); the validation ledger computed; parameter coverage per type reported |
| E3 | The published flyvis ensemble run per eye, mapped onto the real optic-lobe neurons by type and column; LIF elsewhere | mapping coverage reported (share of optic-lobe neurons with a model cell); ledger computed |
| E4 | E2 plus spike-frequency adaptation, per-connection saturation and fan-in normalisation, each parameter cited | ledger computed and compared with E2 row by row |
| N1-N3 | Degree-preserving rewiring, size-matched random graph, sign shuffle, applied to E2 and E4 | same protocol, same seeds, reported beside every E2/E4 result |
| V1 | Hassenstein-Reichardt correlator on the photoreceptor signals | local motion per column on every motion cell; flow error reported |
| V2 | Classical optic flow on the eye mosaics, depth from parallax with known ego-motion, ego-motion-residual segmentation | depth and masks on every cell with ground truth; refusal where depth is unobservable (pure rotation) |
| V3 | T4/T5 population vector to local motion to depth from parallax (no training) | as V2, read from the real T4/T5 activity |
| V4 | LPLC2/LC4 time-to-contact readout | time to contact against the analytic truth on the loom and wall cases |
| V5 | Figure-ground by relative motion on the lobula plate | masks against the truth on the figure-ground cells |
| V6 | Learned ridge readout from real optic-lobe activity (depth, figure-ground) | trained on the train split only; validation used for the penalty; held-out metrics; weights exported for the live lane |
| V7 | Learned hexagonal-lattice network from real optic-lobe activity | as V6, with a checkpoint manifest and an ONNX export that passes parity |
| V8 | Depth Anything V2 small on the full-resolution render of each eye's view | an upper-bound reference, labelled as not the fly; held-out metrics |

## 7. Cases and coverage

Thirteen cases in six categories; every case varies one physical parameter over at least six values; every variant is
rendered for both eyes with ground truth. Splits for the learned readouts group by scene layout and stimulus seed, so
no layout or seed reaches both train and test.

| Category | Case | Varied parameter | Why it exists |
|---|---|---|---|
| Motion primitives | C01 gratings | temporal frequency (8 directions each) | direction selectivity, optomotor drive |
| | C02 moving edges | speed (ON and OFF, 8 directions) | ON/OFF pathways, T4 versus T5 |
| | C03 flashes | contrast | polarity of the lamina and medulla |
| Looming and collision | C04 looming disc | size-to-speed ratio l/v | LPLC2 and LC4 to the giant fibre, escape |
| | C05 receding disc | l/v | negative control for C04 |
| | C06 wall approach in flight | approach speed | time to contact, depth |
| Self-motion | C07 yaw rotation | angular velocity | optomotor; depth unobservable (control for V2, V3) |
| | C08 corridor translation | forward speed | depth from parallax |
| Objects and figure-ground | C09 small target | target size | small-object channel (LC11) |
| | C10 figure over ground | relative speed | segmentation by relative motion |
| Social and natural | C11 rival fly | trajectory | LC10, courtship pursuit (a known gap of the raw wiring) |
| | C12 natural flights | scene and path | everything at once, on natural statistics |
| Controls | C13 dark and static | luminance, duration | spontaneous activity; nothing should move |

## 8. The oracle

- **Geometry is exact.** The scenes are ours, so depth along each ommatidium's ray, object masks, optic flow and time
  to contact are computed analytically from the scene, not estimated.
- **Physiology bounds the engines.** Engine rows are judged against published measurements with their DOIs: T4/T5
  direction selectivity and preferred directions (Maisak et al. 2013), LPLC2 looming selectivity (Klapoetke et al.
  2017), LC4/LPLC2 input to the giant fibre and escape (Ache et al. 2019; von Reyn et al. 2014). The escape criterion
  is mechanistic: DNp01 spikes during a loom and stays silent for recede and static controls.
- **Nulls decide attribution.** A claim that the wiring does something is a paired difference against N1-N3 with an
  interval, reported beside the raw number, and refuted before it is published.

## 9. Deploy driver

The product is public, so the target is GitHub Pages at `destello.fasl-work.com` **if** the measured export is under
900 MB in total and every file is under 90 MB; otherwise static hosting on the ml box at
`destello.ml.fasl-work.com`. **UNDECIDED** until the export is measured (unit U9).

The live lane's speed floor, measured at 1600 x 900 on the reference laptop (RTX 4070 Laptop): the browser engine
advances at least 0.02 s of biological time per second of wall time on WebGPU; below that the live tab says so and
replay stays the default.

## 10. Risks and kill criteria

| Risk | Mitigation | Kill criterion |
|---|---|---|
| The graded optic lobe on neuron-level wiring runs away (a type-level build of the visual system measured a loop gain of 3.07) | E3 as the second regime; spectral bound check; E4 stabilisers | if no engine yields bounded activity with correct T4/T5 preferred directions, the Motion and Depth tabs report the negative result and use V1/V2 as their live content |
| The whole-CNS LIF falls silent or seizes | E4 with cited mechanisms | reported per engine; never tuned per case |
| Browser speed below the floor | slow motion; WebGPU first; WASM fallback; replay default | live tab marked replay only on that device |
| Export over the Pages limits | ml-box static hosting | decided by measurement |
| The connectome adds nothing over nulls for depth or segmentation | report it | a valid, published negative result |
| Package publishing blocked by credentials | pin the engine by git tag | ask Felipe at release time |

## 11. Requirements in force at scaffolding

Requirements of later units live in their feature designs. These hold from the first commit.

```
R-001  THE repository SHALL contain no em-dash and no emoji in any tracked text file.
       Gate: scripts/check_content_standards.py

R-002  THE continuous-integration workflows SHALL run only cheap checks, trigger only on develop, main
       and manual dispatch, carry a concurrency group, and give every job a timeout.
       Gate: scripts/check_ci_budget.py

R-003  IF any template example or placeholder survives instantiation, THEN THE guards SHALL fail.
       Gate: scripts/check_template_residue.py

R-004  THE repository SHALL keep a design document in which every requirement names a gate that exists.
       Gate: scripts/check_sdd.py
```
