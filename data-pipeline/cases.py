"""The 13 cases of the product (SDD section 7) and their variants, as scenes the renderer can draw.

Every stimulus is a ``Stimulus``: its case, its varied parameter and value, its seed and scene layout (which decide
its split), its duration, and a factory for its scene. Frames are rendered at 200 per second, the graded engine's
step; every engine starts from the grey steady state, which is not part of the stimulus.

Directional stimuli (gratings, edges) are mirror-symmetric: each eye sees the pattern in its own local frame, where
0 degrees is front to back and 90 degrees is up, around the eye's centre (72.5 degrees of azimuth). A direction of 0
is therefore progressive motion on both eyes at once.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from rays import Primitive, linear, static
from scene import FlyPath, Scene, noise_texture, textured, uniform

FPS = 200
#: Textures are laid so that one texel spans about 1 degree at the case's nominal viewing distance d (a period of
#: 256 texels over 4.5 d metres): finer texture would alias under the ommatidia's 19-ray acceptance quadrature.
TEXTURE_CORRIDOR_M = 0.45
EYE_CENTRE_AZ = 72.5
GREY = 0.5
SPLITS = (("train", 0.60), ("validation", 0.15), ("calibration", 0.10), ("test", 0.15))


@dataclass
class Stimulus:
    case: str
    title: str
    parameter: str
    value: float
    variant: str
    seed: int
    layout: str
    duration_s: float
    scene: Callable[[], Scene]
    extra: dict = field(default_factory=dict)

    @property
    def frames(self) -> int:
        return int(round(self.duration_s * FPS))

    @property
    def split(self) -> str:
        return split_of(self.layout)


def split_of(layout: str) -> str:
    """A layout's split, from a hash of its id: stable, and the same for every variant that shares the layout."""
    u = int(hashlib.sha256(layout.encode("utf-8")).hexdigest()[:8], 16) / 2 ** 32
    edge = 0.0
    for name, share in SPLITS:
        edge += share
        if u < edge:
            return name
    return SPLITS[-1][0]


# ------------------------------------------------------------------------------------- patterns seen per eye

def _eye_coords(points: np.ndarray, centre: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mirror-symmetric eye coordinates of a direction: x = |azimuth| - 72.5 (toward the back), y = elevation."""
    v = points - centre[None, :]
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    az = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    el = np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))
    return np.abs(az) - EYE_CENTRE_AZ, el


def eye_grating(wavelength_deg: float, direction_deg: float, temporal_hz: float, contrast: float = 1.0):
    theta = np.deg2rad(direction_deg)

    def pattern(points, prim, t):
        x, y = _eye_coords(points, prim.position(t))
        phase = (x * np.cos(theta) + y * np.sin(theta)) / wavelength_deg - temporal_hz * t
        return GREY + GREY * contrast * np.sin(2 * np.pi * phase)
    return pattern


def eye_edge(direction_deg: float, speed_deg_s: float, polarity: int, start_deg: float):
    theta = np.deg2rad(direction_deg)
    target = 1.0 if polarity == 1 else 0.0

    def pattern(points, prim, t):
        x, y = _eye_coords(points, prim.position(t))
        return np.where(x * np.cos(theta) + y * np.sin(theta) < start_deg + speed_deg_s * t, target, GREY)
    return pattern


def step(level: float, start_s: float, stop_s: float):
    return lambda points, prim, t: np.full(len(points), level if start_s <= t < stop_s else GREY)


def drum(pattern, radius: float = 0.3) -> Primitive:
    """A cylinder around the fly carrying ``pattern`` (the panorama)."""
    return Primitive("cylinder", 1, pattern, radius=radius)


# ------------------------------------------------------------------------------------------------ the cases

def _c01() -> list[Stimulus]:
    out = []
    for hz in (0.5, 1, 2, 4, 8, 16):
        for d in range(0, 360, 45):
            out.append(Stimulus("C01", "gratings", "temporal_hz", hz, f"f{hz:g}-d{d}", 0, f"C01-f{hz:g}-d{d}", 0.6,
                                lambda hz=hz, d=d: Scene([drum(eye_grating(20.0, d, hz))]),
                                {"direction_deg": d, "wavelength_deg": 20.0}))
    return out


def _c02() -> list[Stimulus]:
    out = []
    for speed in (30, 60, 90, 120, 180, 240):
        for d in range(0, 360, 45):
            for pol in (1, 0):
                out.append(Stimulus("C02", "moving edges", "speed_deg_s", speed, f"s{speed}-d{d}-{'on' if pol else 'off'}",
                                    0, f"C02-s{speed}-d{d}-{pol}", 80.0 / speed + 0.05,
                                    lambda s=speed, d=d, p=pol: Scene([drum(eye_edge(d, s, p, -40.0))]),
                                    {"direction_deg": d, "polarity": pol, "sweep_deg": 80.0}))
    return out


def _c03() -> list[Stimulus]:
    return [Stimulus("C03", "flashes", "contrast", c, f"c{c:+g}", 0, f"C03-c{c:+g}", 0.7,
                     lambda c=c: Scene([drum(step(GREY * (1 + c), 0.1, 0.4))]), {"on_s": 0.1, "off_s": 0.4})
            for c in (-1.0, -0.6, -0.3, 0.3, 0.6, 1.0)]


LOOM_RADIUS = 0.01                     # m
LOOM_AZ = 60.0                         # degrees toward the fly's left: the left eye's frontal-lateral field
LOOM_CONTACT_S = 0.8


def _loom_direction() -> np.ndarray:
    a = np.deg2rad(LOOM_AZ)
    return np.array([np.cos(a), np.sin(a), 0.0])


def _c04() -> list[Stimulus]:
    out = []
    for lv in (10, 20, 40, 60, 80, 120):
        speed = LOOM_RADIUS / (lv / 1000.0)
        u = _loom_direction()
        start = u * (LOOM_RADIUS + speed * LOOM_CONTACT_S)
        out.append(Stimulus("C04", "looming disc", "l_over_v_ms", lv, f"lv{lv}", 0, f"C04-lv{lv}", LOOM_CONTACT_S - 0.02,
                            lambda s=start, v=-u * speed: Scene([Primitive("sphere", 2, uniform(0.0), position=linear(s, v),
                                                                          radius=LOOM_RADIUS)]),
                            {"radius_m": LOOM_RADIUS, "speed_m_s": speed, "contact_s": LOOM_CONTACT_S,
                             "azimuth_deg": LOOM_AZ}))
    return out


def _c05() -> list[Stimulus]:
    out = []
    for lv in (10, 20, 40, 60, 80, 120):
        speed = LOOM_RADIUS / (lv / 1000.0)
        u = _loom_direction()
        start = u * (LOOM_RADIUS * 1.5)
        out.append(Stimulus("C05", "receding disc", "l_over_v_ms", lv, f"lv{lv}", 0, f"C05-lv{lv}", 0.8,
                            lambda s=start, v=u * speed: Scene([Primitive("sphere", 2, uniform(0.0), position=linear(s, v),
                                                                         radius=LOOM_RADIUS)]),
                            {"radius_m": LOOM_RADIUS, "speed_m_s": speed, "azimuth_deg": LOOM_AZ}))
    return out


def _c06() -> list[Stimulus]:
    out = []
    for k, speed in enumerate((0.1, 0.2, 0.3, 0.5, 0.7, 1.0)):
        seed = 600 + k
        tex = noise_texture(seed)
        start = speed * 1.0 + 0.02                             # contact would come at 1 s; the case ends at 0.8 s
        out.append(Stimulus("C06", "wall approach", "speed_m_s", speed, f"v{speed:g}", seed, f"tex{seed}", 0.8,
                            lambda tex=tex, x=start, v=speed: Scene(
                                [Primitive("plane", 3, textured(tex, 1.3), position=static((x, 0.0, 0.0)),
                                           normal=(1.0, 0.0, 0.0), u_axis=(0.0, 1.0, 0.0), v_axis=(0.0, 0.0, 1.0)),
                                 drum(uniform(GREY), radius=5.0)],
                                fly=FlyPath(position=linear((0.0, 0.0, 0.0), (v, 0.0, 0.0)))),
                            {"wall_start_m": start}))
    return out


def _c07() -> list[Stimulus]:
    out = []
    for k, w in enumerate((30, 60, 120, 240, 360, 500)):
        seed = 700 + k
        tex = noise_texture(seed)
        out.append(Stimulus("C07", "yaw rotation", "omega_deg_s", w, f"w{w}", seed, f"tex{seed}", 1.0,
                            lambda tex=tex, w=w: Scene([Primitive("cylinder", 1, textured(tex, 1.3), radius=0.3)],
                                                       fly=FlyPath(heading=lambda t: np.deg2rad(w) * t))))
    return out


def _corridor(tex_left, tex_right, tex_floor, half_width=0.1, height=0.1) -> list[Primitive]:
    return [Primitive("plane", 4, textured(tex_left, TEXTURE_CORRIDOR_M), position=static((0.0, half_width, 0.0)),
                      normal=(0.0, 1.0, 0.0), u_axis=(1.0, 0.0, 0.0), v_axis=(0.0, 0.0, 1.0)),
            Primitive("plane", 5, textured(tex_right, TEXTURE_CORRIDOR_M), position=static((0.0, -half_width, 0.0)),
                      normal=(0.0, 1.0, 0.0), u_axis=(1.0, 0.0, 0.0), v_axis=(0.0, 0.0, 1.0)),
            Primitive("plane", 6, textured(tex_floor, TEXTURE_CORRIDOR_M), position=static((0.0, 0.0, -height / 2)),
                      normal=(0.0, 0.0, 1.0), u_axis=(1.0, 0.0, 0.0), v_axis=(0.0, 1.0, 0.0))]


def _c08() -> list[Stimulus]:
    out = []
    for k, speed in enumerate((0.1, 0.2, 0.3, 0.5, 0.7, 1.0)):
        seed = 800 + k
        texs = [noise_texture(seed * 10 + i) for i in range(3)]
        out.append(Stimulus("C08", "corridor", "speed_m_s", speed, f"v{speed:g}", seed, f"tex{seed}", 1.0,
                            lambda texs=texs, v=speed: Scene(_corridor(*texs), background=0.8,
                                                             fly=FlyPath(position=linear((0, 0, 0), (v, 0, 0))))))
    return out


def _c09() -> list[Stimulus]:
    out = []
    distance = 0.2
    for size in (2, 3, 5, 8, 12, 20):
        radius = distance * np.tan(np.deg2rad(size) / 2)
        omega = np.deg2rad(100.0)                                # 100 degrees per second across the left eye

        def position(t, r=distance, w=omega):
            a = np.deg2rad(20.0) + w * t
            return np.array([r * np.cos(a), r * np.sin(a), 0.0])
        out.append(Stimulus("C09", "small target", "size_deg", size, f"z{size}", 0, f"C09-z{size}", 1.0,
                            lambda rad=radius, pos=position: Scene(
                                [Primitive("sphere", 7, uniform(0.0), position=pos, radius=rad),
                                 drum(uniform(GREY), radius=2.0)]),
                            {"distance_m": distance, "path_deg": [20.0, 120.0]}))
    return out


def _c10() -> list[Stimulus]:
    out = []
    for k, rel in enumerate((10, 30, 60, 90, 120, 180)):
        seed = 1000 + k
        ground, figure = noise_texture(seed), noise_texture(seed + 500)
        distance = 0.15
        omega = np.deg2rad(rel)

        def position(t, d=distance, w=omega):
            a = np.deg2rad(40.0) + w * t
            return np.array([d * np.cos(a), d * np.sin(a), 0.0])

        def figure_plane(tex=figure, pos=position):
            p = Primitive("plane", 8, textured(tex, 0.68), position=pos, normal=(1.0, 0.0, 0.0),
                          u_axis=(0.0, 1.0, 0.0), v_axis=(0.0, 0.0, 1.0), half_extent=(0.02, 0.02))
            return p
        out.append(Stimulus("C10", "figure over ground", "relative_deg_s", rel, f"r{rel}", seed, f"tex{seed}", 0.8,
                            lambda ground=ground, fp=figure_plane: Scene(
                                [_facing(fp()), Primitive("cylinder", 1, textured(ground, 1.8), radius=0.4)]),
                            {"figure_distance_m": distance, "figure_size_m": 0.04}))
    return out


def _facing(plane: Primitive) -> Primitive:
    """Turn a plane patch to face the fly (its normal along its position) at every moment."""
    base = plane.position

    class Facing(Primitive):
        def hit(self, origin, direction, t):
            c = base(t)
            n = c / (np.linalg.norm(c) + 1e-12)
            u = np.cross([0.0, 0.0, 1.0], n)
            u = u / (np.linalg.norm(u) + 1e-12)
            self.normal, self.u_axis, self.v_axis = tuple(n), tuple(u), tuple(np.cross(n, u))
            return Primitive.hit(self, origin, direction, t)
    return Facing(**{k: getattr(plane, k) for k in ("kind", "object_id", "pattern", "position", "radius", "axes",
                                                     "normal", "u_axis", "v_axis", "half_extent", "heading")})


def _c11() -> list[Stimulus]:
    out = []
    for seed in range(1100, 1106):
        rng = np.random.default_rng(seed)
        base_az, drift = rng.uniform(20, 70), rng.uniform(-60, 60)
        radius, wobble = rng.uniform(0.006, 0.015), rng.uniform(0.001, 0.004)
        freq = rng.uniform(1.0, 3.0)

        def position(t, a0=base_az, dr=drift, r=radius, wb=wobble, f=freq):
            a = np.deg2rad(a0 + dr * t)
            rr = r + wb * np.sin(2 * np.pi * f * t)
            return np.array([rr * np.cos(a), rr * np.sin(a), 0.001 * np.sin(2 * np.pi * f * t / 2)])

        def heading(t, a0=base_az, dr=drift):
            return np.deg2rad(a0 + dr * t + 90.0)
        out.append(Stimulus("C11", "rival fly", "path_seed", seed, f"p{seed}", seed, f"path{seed}", 1.5,
                            lambda pos=position, hd=heading: Scene(
                                [Primitive("ellipsoid", 9, uniform(0.05), position=pos, axes=(0.00125, 0.0005, 0.0005),
                                           heading=hd), drum(uniform(0.7), radius=2.0)]),
                            {"distance_m": [radius - wobble, radius + wobble]}))
    return out


def _c12() -> list[Stimulus]:
    out = []
    for seed in range(1200, 1206):
        rng = np.random.default_rng(seed)
        ground = noise_texture(seed)
        trees = []
        for i in range(10):
            a, r = rng.uniform(0, 2 * np.pi), rng.uniform(0.15, 0.8)
            trees.append(((r * np.cos(a), r * np.sin(a), 0.0), rng.uniform(0.01, 0.04), noise_texture(seed * 20 + i)))
        speed, turn = rng.uniform(0.1, 0.4), rng.uniform(-90, 90)

        def scene(ground=ground, trees=trees, v=speed, w=turn):
            prims = [Primitive("plane", 10, textured(ground, 0.9), position=static((0.0, 0.0, -0.05)),
                               normal=(0.0, 0.0, 1.0), u_axis=(1.0, 0.0, 0.0), v_axis=(0.0, 1.0, 0.0))]
            prims += [Primitive("cylinder", 11 + i, textured(tex, 1.0), position=static(c), radius=rad)
                      for i, (c, rad, tex) in enumerate(trees)]
            fly = FlyPath(position=lambda t: np.array([v * t * np.cos(np.deg2rad(w) * t / 2),
                                                        v * t * np.sin(np.deg2rad(w) * t / 2), 0.0]),
                          heading=lambda t: np.deg2rad(w) * t)
            return Scene(prims, fly=fly, background=0.85)
        out.append(Stimulus("C12", "natural flights", "scene_seed", seed, f"n{seed}", seed, f"forest{seed}", 1.5, scene,
                            {"speed_m_s": speed, "turn_deg_s": turn}))
    return out


def _c13() -> list[Stimulus]:
    return [Stimulus("C13", "dark and static", "luminance", level, f"l{level:g}", 0, f"C13-l{level:g}", 1.0,
                     lambda level=level: Scene([drum(uniform(level))])) for level in (0.0, 0.1, 0.3, 0.5, 0.7, 1.0)]


CASES = {"C01": _c01, "C02": _c02, "C03": _c03, "C04": _c04, "C05": _c05, "C06": _c06, "C07": _c07, "C08": _c08,
         "C09": _c09, "C10": _c10, "C11": _c11, "C12": _c12, "C13": _c13}


def all_stimuli() -> list[Stimulus]:
    return [s for make in CASES.values() for s in make()]
