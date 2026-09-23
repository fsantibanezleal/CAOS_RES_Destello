# Overview: from the connectome to a nervous system you can watch

## Two repositories

| Repository | Role |
|---|---|
| `CAOS_FlyCNS` | the engine, published as `flycns` (Python) and `@fasl-work/flycns` (browser): compiles MaleCNS into a signed graph with positions and per-eye columns, models the two compound eyes, and simulates the whole CNS with a graded optic lobe and the published spiking model elsewhere |
| `CAOS_RES_Destello` (this one) | the product: the pipeline that renders the cases, runs every engine and readout over them, evaluates and exports; the companion web; this wiki |

## The path

```
MaleCNS v1.0 (hash-checked) --flycns--> compiled graph + eyes
cases and variants (our renderer) ------> each eye's input + exact ground truth
                                          |
                     engines E1-E4, nulls N1-N3 (offline, GPU)
                                          |
                               recordings of activity
                                          |
                  readouts V1-V8 (motion, depth, time to contact, figure-ground)
                                          |
                      evaluation against geometry and physiology
                                          |
                  export: live graph, anatomy, recordings, metrics, manifest
                                          |
             companion web: replay by default, live engine where it passes its gates
```

## Lanes

| Lane | Runs | Why there |
|---|---|---|
| Offline | every engine, null and readout over the whole matrix; training | minutes of GPU per simulated second over thousands of runs |
| Replay | the committed recordings | the page never waits for a simulation |
| Live | the browser engine and the light readouts, on the visitor's stimuli | accepted only after parity with the offline engine and a measured speed floor |

The full statement, with the acceptance criterion of every method and the thresholds, is the design document.
