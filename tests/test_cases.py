"""The case matrix: every case with its variants, clean splits, and rendering that is exactly repeatable.

Synthetic eyes stand in for the MaleCNS eye model (the renderer takes any set of directions), so these run anywhere.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import replace

import numpy as np
import pytest
from cases import CASES, FPS, SPLITS, all_stimuli, split_of
from render_cases import LUMINANCE_SCALE, load_stimulus, render_all, render_stimulus


def eyes(n: int = 40) -> np.ndarray:
    """n directions per side, spread over each eye's field."""
    rng = np.random.default_rng(0)
    az = np.deg2rad(rng.uniform(-10, 155, size=2 * n)) * np.r_[np.ones(n), -np.ones(n)]
    el = np.deg2rad(rng.uniform(-70, 70, size=2 * n))
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], axis=1)


def lattice(n: int = 12) -> np.ndarray:
    return eyes(n).reshape(2, n, 3)


def test_every_case_has_its_variants_and_clean_splits(tmp_path):
    stimuli = all_stimuli()
    assert sorted({s.case for s in stimuli}) == sorted(CASES) and len(CASES) == 13
    by_case = defaultdict(set)
    for s in stimuli:
        by_case[s.case].add(s.value)
        assert s.frames == int(round(s.duration_s * FPS)) and s.frames > 0
    assert all(len(values) >= 6 for values in by_case.values()), by_case
    assert len({(s.case, s.variant) for s in stimuli}) == len(stimuli)          # variant names are unique per case
    # a layout lies wholly in one split, and the split sizes are near 60/15/10/15
    layouts = defaultdict(set)
    for s in stimuli:
        layouts[s.layout].add(s.split)
    assert all(len(v) == 1 for v in layouts.values())
    counts = defaultdict(int)
    for layout in layouts:
        counts[split_of(layout)] += 1
    for name, share in SPLITS:
        assert abs(counts[name] / len(layouts) - share) < 0.10, (name, counts)
    # every stimulus renders, both eyes and the lattices, with sane values and truth
    cols, lat = eyes(), lattice()
    for s in stimuli:
        short = replace(s, duration_s=2 / FPS)
        out = render_stimulus(short, cols, lat)
        assert out["luminance_u16"].shape == (2, len(cols)) and out["lattice_luminance_u16"].shape == (2, 2, 12)
        assert out["luminance_u16"].max() <= LUMINANCE_SCALE
        assert np.isfinite(out["flow_deg_s"]).all()
        assert (out["depth_m"] > 0).all()
    # the index lists what was rendered, with its split
    picked = [s for s in stimuli if s.case in ("C03", "C04")][:4]
    index = render_all([replace(s, duration_s=3 / FPS) for s in picked], cols, lat, tmp_path, progress=lambda m: None)
    on_disk = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert on_disk == index and [e["split"] for e in index] == [s.split for s in picked]
    loaded = load_stimulus(tmp_path / index[0]["directory"])
    assert loaded["luminance"].dtype == np.float32 and loaded["meta"]["case"] == picked[0].case


def test_rendering_is_deterministic():
    textured = next(s for s in all_stimuli() if s.case == "C12")
    short = replace(textured, duration_s=4 / FPS)
    a = render_stimulus(short, eyes(), lattice())
    b = render_stimulus(short, eyes(), lattice())
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert a["luminance_u16"].std() > 0                    # a textured world, not a blank one


def test_looming_case_contacts_at_its_stated_time():
    loom = next(s for s in all_stimuli() if s.case == "C04" and s.value == 40)
    ahead = np.array([[np.cos(np.deg2rad(60)), np.sin(np.deg2rad(60)), 0.0]])
    out = render_stimulus(loom, ahead, lattice())
    t = np.arange(loom.frames) / FPS
    expected = loom.extra["contact_s"] - t                       # the sphere's surface reaches the eye at contact
    assert out["time_to_contact_s"][:, 0] == pytest.approx(expected, abs=2e-3)
