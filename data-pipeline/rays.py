"""Analytic ray casting: the first hit of each ray on spheres, planes and the inside of a panoramic cylinder.

Every primitive has a closed-form intersection, so depth, the object hit and the hit point are exact. Rays are given
in the world frame (metres); a primitive is placed at time ``t`` by its ``position(t)``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

Pattern = Callable[[np.ndarray, "Primitive", float], np.ndarray]   # (hit points, primitive, t) -> luminance


def static(point) -> Callable[[float], np.ndarray]:
    p = np.asarray(point, dtype=np.float64)
    return lambda t: p


def linear(start, velocity) -> Callable[[float], np.ndarray]:
    s, v = np.asarray(start, dtype=np.float64), np.asarray(velocity, dtype=np.float64)
    return lambda t: s + v * t


@dataclass
class Primitive:
    """A surface: its kind and size, where it is at each moment, and what it looks like."""

    kind: str                                   # "sphere", "plane", "cylinder" (seen from inside), "ellipsoid"
    object_id: int
    pattern: Pattern
    position: Callable[[float], np.ndarray] = field(default_factory=lambda: static((0.0, 0.0, 0.0)))
    radius: float = 1.0                         # sphere, cylinder; ellipsoid: the semi-axes are ``axes``
    axes: tuple[float, float, float] = (1.0, 1.0, 1.0)
    normal: tuple[float, float, float] = (1.0, 0.0, 0.0)          # plane
    u_axis: tuple[float, float, float] = (0.0, 1.0, 0.0)          # plane: the in-plane axes and half extents
    v_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    half_extent: tuple[float, float] = (np.inf, np.inf)
    heading: Callable[[float], float] = field(default_factory=lambda: (lambda t: 0.0))   # ellipsoid yaw

    def hit(self, origin: np.ndarray, direction: np.ndarray, t: float) -> np.ndarray:
        """Distance along each ray (rows of ``direction``, unit length) to this surface; inf where it misses."""
        c = self.position(t)
        o = np.asarray(origin, dtype=np.float64) - c
        d = direction
        if self.kind == "sphere":
            return _quadratic_near(np.einsum("ij,ij->i", d, d), 2 * d @ o, o @ o - self.radius ** 2)
        if self.kind == "ellipsoid":
            yaw = self.heading(t)
            rot = np.array([[np.cos(yaw), np.sin(yaw), 0.0], [-np.sin(yaw), np.cos(yaw), 0.0], [0.0, 0.0, 1.0]])
            scale = 1.0 / np.asarray(self.axes)
            os_ = (rot @ o) * scale
            ds = (d @ rot.T) * scale
            return _quadratic_near(np.einsum("ij,ij->i", ds, ds), 2 * ds @ os_, os_ @ os_ - 1.0)
        if self.kind == "pillar":                              # vertical cylinder seen from outside (a trunk)
            a = d[:, 0] ** 2 + d[:, 1] ** 2
            b = 2 * (d[:, 0] * o[0] + d[:, 1] * o[1])
            s = _quadratic_near(np.maximum(a, 1e-15), b, o[0] ** 2 + o[1] ** 2 - self.radius ** 2)
            return np.where(a > 1e-15, s, np.inf)
        if self.kind == "cylinder":                            # vertical axis through c, seen from inside
            a = d[:, 0] ** 2 + d[:, 1] ** 2
            b = 2 * (d[:, 0] * o[0] + d[:, 1] * o[1])
            cc = o[0] ** 2 + o[1] ** 2 - self.radius ** 2
            disc = b * b - 4 * a * cc
            with np.errstate(invalid="ignore", divide="ignore"):
                far = (-b + np.sqrt(np.maximum(disc, 0.0))) / (2 * a)
            return np.where((disc >= 0) & (a > 1e-15) & (far > 1e-12), far, np.inf)
        if self.kind == "plane":
            n = np.asarray(self.normal, dtype=np.float64)
            denom = d @ n
            with np.errstate(divide="ignore", invalid="ignore"):
                s = -(o @ n) / denom
            s = np.where((np.abs(denom) > 1e-15) & (s > 1e-12), s, np.inf)
            if np.isfinite(self.half_extent).any():
                p = o[None, :] + np.where(np.isfinite(s), s, 0.0)[:, None] * d
                inside = (np.abs(p @ np.asarray(self.u_axis)) <= self.half_extent[0]) & (
                    np.abs(p @ np.asarray(self.v_axis)) <= self.half_extent[1])
                s = np.where(inside, s, np.inf)
            return s
        raise ValueError(f"unknown primitive {self.kind}")


def _quadratic_near(a: np.ndarray, b: np.ndarray, c: float | np.ndarray) -> np.ndarray:
    """The smallest positive root of a s^2 + b s + c = 0, inf where there is none."""
    disc = b * b - 4 * a * c
    root = np.sqrt(np.maximum(disc, 0.0))
    near = (-b - root) / (2 * a)
    far = (-b + root) / (2 * a)
    s = np.where(near > 1e-12, near, np.where(far > 1e-12, far, np.inf))
    return np.where(disc >= 0, s, np.inf)


def first_hit(primitives: list[Primitive], origin: np.ndarray, direction: np.ndarray,
              t: float) -> tuple[np.ndarray, np.ndarray]:
    """(distance, index of the primitive hit or -1) for each ray."""
    best = np.full(len(direction), np.inf)
    which = np.full(len(direction), -1, dtype=np.int64)
    for k, prim in enumerate(primitives):
        s = prim.hit(origin, direction, t)
        closer = s < best
        best = np.where(closer, s, best)
        which = np.where(closer, k, which)
    return best, which


# ------------------------------------------------------------------------------------------------ acceptance

ACCEPTANCE_FWHM_DEG = 8.23                     # R1-R6, dark-adapted (Gonzalez-Bellido et al. 2011)


def acceptance_offsets(fwhm_deg: float = ACCEPTANCE_FWHM_DEG) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The 19 sample rays of one ommatidium: (radius in radians, angle around the axis, weight), the centre and rings
    of 6 and 12 rays at one and two sigma of the Gaussian acceptance, weighted by the Gaussian and normalised."""
    sigma = np.deg2rad(fwhm_deg) / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    radius = np.r_[0.0, np.full(6, sigma), np.full(12, 2 * sigma)]
    angle = np.r_[0.0, np.arange(6) * np.pi / 3, np.arange(12) * np.pi / 6 + np.pi / 12]
    weight = np.exp(-radius ** 2 / (2 * sigma ** 2))
    return radius, angle, weight / weight.sum()


def sample_directions(directions: np.ndarray, fwhm_deg: float = ACCEPTANCE_FWHM_DEG) -> tuple[np.ndarray, np.ndarray]:
    """For unit ``directions`` (n, 3): the (n, 19, 3) sample rays around each and their (19,) weights."""
    radius, angle, weight = acceptance_offsets(fwhm_deg)
    d = directions / np.linalg.norm(directions, axis=1, keepdims=True)
    helper = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    e1 = np.cross(d, helper)
    e1 /= np.linalg.norm(e1, axis=1, keepdims=True)
    e2 = np.cross(d, e1)
    rays = (np.cos(radius)[None, :, None] * d[:, None, :]
            + np.sin(radius)[None, :, None] * (np.cos(angle)[None, :, None] * e1[:, None, :]
                                               + np.sin(angle)[None, :, None] * e2[:, None, :]))
    return rays, weight
