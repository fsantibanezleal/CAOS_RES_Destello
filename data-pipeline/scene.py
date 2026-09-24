"""Scenes around the fly, and what each ommatidium sees in them, with the exact truth.

The world frame is metres, z up. The fly's head moves on a path (position, heading); its body frame is x forward, y
left, z up, the frame of ``flycns.eyes``. A frame is rendered at time ``t`` for any set of viewing directions given in
the body frame: each direction is sampled over the ommatidium's Gaussian acceptance (19 rays, ``rays.sample_directions``)
for its luminance, and its central ray gives the truth: depth, the object hit, optic flow and time to contact.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from rays import Primitive, first_hit, sample_directions

BACKGROUND_ID = 0


@dataclass
class FlyPath:
    position: Callable[[float], np.ndarray] = field(default_factory=lambda: (lambda t: np.zeros(3)))
    heading: Callable[[float], float] = field(default_factory=lambda: (lambda t: 0.0))   # yaw, radians


def yaw_matrix(heading: float) -> np.ndarray:
    """Body to world: a rotation about z by ``heading``."""
    c, s = np.cos(heading), np.sin(heading)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


@dataclass
class Scene:
    primitives: list[Primitive]
    fly: FlyPath = field(default_factory=FlyPath)
    background: float = 0.5                                   # the luminance where no surface is hit


@dataclass
class Frame:
    luminance: np.ndarray        # (n,) acceptance-weighted
    depth: np.ndarray            # (n,) metres along the central ray; inf where nothing is hit
    object_id: np.ndarray        # (n,) the primitive's object id; 0 for the background
    flow: np.ndarray             # (n, 2) degrees per second: azimuth (toward the fly's left) and elevation
    time_to_contact: np.ndarray  # (n,) seconds; inf unless the surface point approaches


def _shade(scene: Scene, points: np.ndarray, which: np.ndarray, t: float) -> np.ndarray:
    out = np.full(len(which), scene.background, dtype=np.float64)
    for k, prim in enumerate(scene.primitives):
        m = which == k
        if m.any():
            out[m] = prim.pattern(points[m], prim, t)
    return out


def _body_angles(vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return np.degrees(np.arctan2(unit[:, 1], unit[:, 0])), np.degrees(np.arcsin(np.clip(unit[:, 2], -1, 1)))


def render(scene: Scene, directions: np.ndarray, t: float, dt: float = 1 / 200,
           samples: tuple[np.ndarray, np.ndarray] | None = None) -> Frame:
    """What ``directions`` (n, 3, body frame) see at time ``t``."""
    rays, weight = samples if samples is not None else sample_directions(directions)
    n = len(directions)
    origin = scene.fly.position(t)
    rot = yaw_matrix(scene.fly.heading(t))
    world = rays.reshape(-1, 3) @ rot.T
    s, which = first_hit(scene.primitives, origin, world, t)
    points = origin[None, :] + np.where(np.isfinite(s), s, 0.0)[:, None] * world
    luminance = (_shade(scene, points, which, t).reshape(n, -1) * weight[None, :]).sum(axis=1)

    central = slice(0, None, rays.shape[1])                   # the first sample of each ommatidium is its axis
    s0, w0, p0, d0 = s[central], which[central], points[central], world[central]
    object_id = np.where(w0 >= 0, np.array([p.object_id for p in scene.primitives] + [BACKGROUND_ID])[w0], 0)
    object_id = np.where(w0 >= 0, object_id, BACKGROUND_ID)

    # the same material point half a frame before and after: surfaces move with their primitive; the background is
    # at infinity, fixed in the world
    h = dt / 2
    rel = p0 - np.array([scene.primitives[k].position(t) if k >= 0 else np.zeros(3) for k in w0])
    angles, distances = [], []
    for tt in (t - h, t + h):
        pos = scene.fly.position(tt)
        back = yaw_matrix(scene.fly.heading(tt)).T
        moved = np.array([scene.primitives[k].position(tt) if k >= 0 else np.zeros(3) for k in w0]) + rel
        vec = np.where((w0 >= 0)[:, None], moved - pos[None, :], d0)
        angles.append(_body_angles(vec @ back.T))
        distances.append(np.linalg.norm(moved - pos[None, :], axis=1))
    d_az = (angles[1][0] - angles[0][0] + 180.0) % 360.0 - 180.0
    flow = np.stack([d_az / dt, (angles[1][1] - angles[0][1]) / dt], axis=1)
    closing = -(distances[1] - distances[0]) / dt
    with np.errstate(divide="ignore", invalid="ignore"):
        ttc = np.where((w0 >= 0) & (closing > 1e-9), s0 / closing, np.inf)
    return Frame(luminance=luminance, depth=s0, object_id=object_id.astype(np.int64), flow=flow, time_to_contact=ttc)


# ------------------------------------------------------------------------------------------------------ patterns

def uniform(level: float):
    return lambda points, prim, t: np.full(len(points), level)


def _world_angles(points: np.ndarray, centre: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    v = points - centre[None, :]
    return _body_angles(v)


def grating(wavelength_deg: float, direction_deg: float, temporal_hz: float, contrast: float = 1.0,
            mean: float = 0.5):
    """A sinusoidal grating in the angular coordinates of the surface around its centre, drifting along
    ``direction_deg`` (0: increasing azimuth, toward the fly's left; 90: up) at ``temporal_hz``."""
    theta = np.deg2rad(direction_deg)

    def pattern(points, prim, t):
        az, el = _world_angles(points, prim.position(t))
        phase = (az * np.cos(theta) + el * np.sin(theta)) / wavelength_deg - temporal_hz * t
        return mean + mean * contrast * np.sin(2 * np.pi * phase)
    return pattern


def edge(direction_deg: float, speed_deg_s: float, polarity: int, start_deg: float, mean: float = 0.5):
    """A full-field edge in the surface's angular coordinates: the side it has swept becomes 1 (ON) or 0 (OFF)."""
    theta = np.deg2rad(direction_deg)
    target = 1.0 if polarity == 1 else 0.0

    def pattern(points, prim, t):
        az, el = _world_angles(points, prim.position(t))
        position = az * np.cos(theta) + el * np.sin(theta)
        return np.where(position < start_deg + speed_deg_s * t, target, mean)
    return pattern


def noise_texture(seed: int, size: int = 256, exponent: float = 1.5) -> np.ndarray:
    """A seeded luminance texture in [0, 1], periodic, (size, size), its amplitude spectrum falling as 1/f^exponent
    (1.5: a little smoother than natural images' 1/f, so the eye's sampling does not alias it)."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(size)
    radius = np.hypot(f[:, None], f[None, :])
    radius[0, 0] = 1.0
    spectrum = (rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size))) / radius ** exponent
    spectrum[0, 0] = 0.0
    img = np.real(np.fft.ifft2(spectrum))
    img = (img - img.mean()) / (img.std() + 1e-12)
    return np.clip(0.5 + 0.18 * img, 0.0, 1.0)


def textured(texture: np.ndarray, scale_m: float):
    """A texture laid on a surface: planes by their in-plane coordinates, cylinders by arc length and height,
    spheres and ellipsoids by longitude and latitude, one texture period per ``scale_m`` metres."""
    size = texture.shape[0]

    def pattern(points, prim, t):
        rel = points - prim.position(t)[None, :]
        if prim.kind == "plane":
            u, v = rel @ np.asarray(prim.u_axis), rel @ np.asarray(prim.v_axis)
        elif prim.kind == "cylinder":
            u, v = np.arctan2(rel[:, 1], rel[:, 0]) * prim.radius, rel[:, 2]
        else:
            r = np.linalg.norm(rel, axis=1) + 1e-12
            u, v = np.arctan2(rel[:, 1], rel[:, 0]) * r, np.arcsin(np.clip(rel[:, 2] / r, -1, 1)) * r
        x = (u / scale_m * size) % size
        y = (v / scale_m * size) % size
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - x0, y - y0
        x1, y1 = (x0 + 1) % size, (y0 + 1) % size
        return ((1 - fx) * (1 - fy) * texture[y0 % size, x0 % size] + fx * (1 - fy) * texture[y0 % size, x1]
                + (1 - fx) * fy * texture[y1, x0 % size] + fx * fy * texture[y1, x1])
    return pattern
