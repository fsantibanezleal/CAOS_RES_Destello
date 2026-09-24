"""The dataset stage: render every stimulus of every case for both eyes, with its truth, and index them.

For each stimulus, one directory in the compiled style (``flycns.compiled``; a manifest with the SHA-256 of every
array): per frame and eye column, the luminance, the depth, the object hit, the optic flow and the time to contact;
per frame, the luminance at the 721 columns of flyvis's lattice on each eye (E3's input). ``index.json`` lists every
stimulus with its case, parameter, seed, layout and split.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from cases import FPS, Stimulus, all_stimuli
from flycns.compiled import write_compiled
from rays import sample_directions
from scene import render

SCHEMA = "destello.case/1"
LUMINANCE_SCALE = 65535                      # luminance in [0, 1] stored as uint16: a step of 1.5e-5


def quantise(luminance: np.ndarray) -> np.ndarray:
    return np.round(np.clip(luminance, 0.0, 1.0) * LUMINANCE_SCALE).astype(np.uint16)


def load_stimulus(directory: Path) -> dict[str, np.ndarray]:
    """A rendered stimulus with its luminance back in [0, 1] (float32) and its metadata under ``meta``."""
    from flycns.compiled import read_compiled

    c = read_compiled(Path(directory), schema=SCHEMA)
    out = {name: c[name] for name in c.arrays}
    out["luminance"] = out.pop("luminance_u16").astype(np.float32) / LUMINANCE_SCALE
    out["lattice_luminance"] = out.pop("lattice_luminance_u16").astype(np.float32) / LUMINANCE_SCALE
    out["meta"] = c.manifest["release"]
    return out


def local_to_direction(x_deg: np.ndarray, y_deg: np.ndarray, centre_az: float, centre_el: float,
                       side: str) -> np.ndarray:
    """The inverse of ``flycns.motion.local_frame``: tangent-plane coordinates around an eye's centre (x toward the
    back, y up, azimuthal-equidistant) to body-frame unit directions."""
    x, y = np.deg2rad(np.asarray(x_deg)), np.deg2rad(np.asarray(y_deg))
    rho = np.hypot(x, y)
    bearing = np.arctan2(y, x)
    a0, e0 = math.radians(centre_az), math.radians(centre_el)
    el = np.arcsin(np.sin(e0) * np.cos(rho) + np.cos(e0) * np.sin(rho) * np.sin(bearing))
    az = a0 + np.arctan2(np.cos(bearing) * np.sin(rho) * np.cos(e0), np.cos(rho) - np.sin(e0) * np.sin(el))
    lateral = -1.0 if side == "right" else 1.0
    return np.stack([np.cos(el) * np.cos(az), lateral * np.cos(el) * np.sin(az), np.sin(el)], axis=1)


def column_directions(graph, geometry: dict) -> np.ndarray:
    """Each compiled column's viewing direction (body frame), from the eye model."""
    from flycns.eyes import build_eyes

    eyes = build_eyes(graph["column_side"], graph["column_hex"], graph["column_kind"], geometry)
    out = np.full((len(graph["column_side"]), 3), np.nan)
    for side in ("left", "right"):
        out[eyes[side].column_index] = eyes[side].directions
    return out, eyes


def lattice_directions(lattice, eyes) -> np.ndarray:
    """(2, 721, 3): where flyvis's lattice columns look on the left and the right eye (``flycns.mapped``)."""
    from flycns.mapped import lattice_local_xy
    from flycns.motion import eye_centre

    u = lattice["node_u"][lattice["input_index"][0]].astype(float)
    v = lattice["node_v"][lattice["input_index"][0]].astype(float)
    x, y = lattice_local_xy(u, v)
    out = []
    for side in ("left", "right"):
        eye = eyes[side]
        out.append(local_to_direction(x, y, *eye_centre(eye.azimuth_deg, eye.elevation_deg), side))
    return np.stack(out)


def render_stimulus(stim: Stimulus, columns: np.ndarray, lattice: np.ndarray) -> dict[str, np.ndarray]:
    scene = stim.scene()
    samples_c = sample_directions(columns)
    samples_l = sample_directions(lattice.reshape(-1, 3))
    n, frames = len(columns), stim.frames
    out = {"luminance_u16": np.zeros((frames, n), dtype=np.uint16), "depth_m": np.zeros((frames, n), dtype=np.float32),
           "object_id": np.zeros((frames, n), dtype=np.uint8), "flow_deg_s": np.zeros((frames, n, 2), dtype=np.float32),
           "time_to_contact_s": np.zeros((frames, n), dtype=np.float32),
           "lattice_luminance_u16": np.zeros((frames, 2, lattice.shape[1]), dtype=np.uint16)}
    for k in range(frames):
        t = k / FPS
        f = render(scene, columns, t, 1 / FPS, samples_c)
        out["luminance_u16"][k] = quantise(f.luminance)
        out["depth_m"][k] = f.depth
        out["object_id"][k] = f.object_id
        out["flow_deg_s"][k] = f.flow
        out["time_to_contact_s"][k] = f.time_to_contact
        lat = render(scene, lattice.reshape(-1, 3), t, 1 / FPS, samples_l)
        out["lattice_luminance_u16"][k] = quantise(lat.luminance).reshape(2, -1)
    return out


def meta(stim: Stimulus) -> dict:
    return {"case": stim.case, "title": stim.title, "parameter": stim.parameter, "value": stim.value,
            "variant": stim.variant, "seed": stim.seed, "layout": stim.layout, "split": stim.split,
            "duration_s": stim.duration_s, "frames": stim.frames, "fps": FPS,
            "extra": {k: (v if not isinstance(v, np.ndarray) else v.tolist()) for k, v in stim.extra.items()}}


def run(compiled_dir: Path, geometry_file: Path, lattice_dir: Path, out_dir: Path, cases: list[str] | None = None,
        progress=print) -> list[dict]:
    from flycns.compiled import read_compiled

    graph = read_compiled(compiled_dir, verify=False)
    columns, eyes = column_directions(graph, json.loads(geometry_file.read_text(encoding="utf-8")))
    lattice = lattice_directions(read_compiled(lattice_dir), eyes)
    stimuli = [s for s in all_stimuli() if not cases or s.case in cases]
    return render_all(stimuli, columns, lattice, out_dir, progress)


def render_all(stimuli: list[Stimulus], columns: np.ndarray, lattice: np.ndarray, out_dir: Path,
               progress=print) -> list[dict]:
    """Render (or keep, when already on disk) every stimulus, and write ``index.json``."""
    index = []
    for stim in stimuli:
        target = out_dir / stim.case / stim.variant
        if (target / "manifest.json").is_file():
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        else:
            arrays = render_stimulus(stim, columns, lattice)
            manifest = write_compiled(target, arrays, {"release": meta(stim), "counts": {"frames": stim.frames}},
                                      schema=SCHEMA)
            progress(f"{stim.case} {stim.variant}: {stim.frames} frames")
        index.append({**meta(stim), "directory": f"{stim.case}/{stim.variant}",
                      "arrays": {a["name"]: a["sha256"] for a in manifest["arrays"]}})
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(index, indent=1) + "\n"
    (out_dir / "index.json").write_text(text, encoding="utf-8", newline="\n")
    return index
