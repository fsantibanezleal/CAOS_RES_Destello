"""The renderer against geometry whose answer is a closed form."""

from __future__ import annotations

import numpy as np
import pytest
from rays import Primitive, acceptance_offsets, first_hit, linear, sample_directions, static
from scene import FlyPath, Scene, render, textured, uniform


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def directions_on_equator(n: int = 72) -> np.ndarray:
    az = np.deg2rad(np.arange(n) * 360.0 / n)
    return np.stack([np.cos(az), np.sin(az), np.zeros(n)], axis=1)


def test_rays_hit_what_geometry_says():
    sphere = Primitive("sphere", 1, uniform(0.0), position=static((2.0, 0.0, 0.0)), radius=0.5)
    wall = Primitive("plane", 2, uniform(1.0), position=static((3.0, 0.0, 0.0)), normal=(1.0, 0.0, 0.0))
    small = Primitive("plane", 3, uniform(1.0), position=static((0.0, 1.0, 0.0)), normal=(0.0, 1.0, 0.0),
                      u_axis=(1.0, 0.0, 0.0), v_axis=(0.0, 0.0, 1.0), half_extent=(0.1, 0.1))
    drum = Primitive("cylinder", 4, uniform(0.5), radius=5.0)
    rays = unit([[1, 0, 0], [1, 0.1, 0], [0, 1, 0], [0, 1, 0.5], [-1, 0, 0], [0, 0, 1]])
    s, which = first_hit([sphere, wall, small, drum], np.zeros(3), rays, 0.0)
    assert s[0] == pytest.approx(1.5, abs=1e-9) and which[0] == 0                # sphere in front of the wall
    # a ray 0.1 off axis meets the sphere where |s d - c| = r
    d = rays[1]
    expected = d @ [2, 0, 0] - np.sqrt((d @ [2, 0, 0]) ** 2 - (4 - 0.25))
    assert s[1] == pytest.approx(expected, abs=1e-9) and which[1] == 0
    assert s[2] == pytest.approx(1.0, abs=1e-9) and which[2] == 2                 # the small square
    assert s[3] == pytest.approx(5.0 / np.hypot(1, 0) * np.linalg.norm([0, 1, 0.5]) / 1.0, abs=1e-9)
    assert which[3] == 3                                                         # above the square: the drum
    assert s[4] == pytest.approx(5.0, abs=1e-9) and which[4] == 3
    assert np.isinf(s[5]) and which[5] == -1                                     # straight up: nothing
    # an ellipsoid's axes, turned by its heading
    body = Primitive("ellipsoid", 5, uniform(0.0), position=static((0.0, 0.0, 0.0)), axes=(2.0, 1.0, 1.0),
                     heading=lambda t: np.pi / 2)
    s, _ = first_hit([body], np.array([0.0, -5.0, 0.0]), unit([[0, 1, 0]]), 0.0)
    assert s[0] == pytest.approx(3.0, abs=1e-9)                                  # the long axis now along y


def test_acceptance_sampling_is_normalised_and_centred():
    radius, angle, weight = acceptance_offsets(8.23)
    sigma = np.deg2rad(8.23) / (2 * np.sqrt(2 * np.log(2)))
    assert len(weight) == 19 and weight.sum() == pytest.approx(1.0)
    assert np.allclose(weight[1:7] / weight[0], np.exp(-0.5)) and np.allclose(weight[7:] / weight[0], np.exp(-2))
    assert radius[1] == pytest.approx(sigma) and radius[-1] == pytest.approx(2 * sigma)
    dirs = directions_on_equator()
    rays, w = sample_directions(dirs)
    assert np.allclose(np.linalg.norm(rays, axis=2), 1.0)
    assert np.allclose(rays[:, 0, :], dirs)
    angle_off = np.degrees(np.arccos(np.clip(np.einsum("nkj,nj->nk", rays, dirs), -1, 1)))
    assert np.allclose(angle_off[:, 1:7], np.degrees(sigma)) and np.allclose(angle_off[:, 7:], 2 * np.degrees(sigma))
    # a uniform world is its luminance, exactly
    frame = render(Scene([Primitive("cylinder", 1, uniform(0.37), radius=3.0)]), dirs, 0.0)
    assert np.allclose(frame.luminance, 0.37)
    # a small bright sphere lights most the ommatidium that looks at it
    target = Primitive("sphere", 2, uniform(1.0), position=static((np.cos(0.5) * 2, np.sin(0.5) * 2, 0.0)),
                       radius=0.05)
    frame = render(Scene([target], background=0.0), dirs, 0.0)
    looks = np.argmax(dirs @ unit([np.cos(0.5), np.sin(0.5), 0.0]))
    assert np.argmax(frame.luminance) == looks and frame.object_id[looks] == 2


def test_flow_truth_matches_yaw_rotation():
    omega = np.deg2rad(120.0)                                                    # 120 degrees per second, to the left
    drum = Primitive("cylinder", 1, textured(np.random.default_rng(0).uniform(size=(64, 64)), 0.5), radius=1.0)
    scene = Scene([drum], fly=FlyPath(heading=lambda t: omega * t))
    frame = render(scene, directions_on_equator(), 0.3)
    # turning left moves the world rightward: every ommatidium sees -omega in azimuth, nothing in elevation
    assert np.allclose(frame.flow[:, 0], -120.0, rtol=5e-3)
    assert np.allclose(frame.flow[:, 1], 0.0, atol=1e-6)
    assert np.allclose(frame.depth, 1.0)


def test_looming_sphere_truth():
    speed, radius, start = 1.0, 0.02, 0.5                                        # m/s, m, m
    ball = Primitive("sphere", 1, uniform(0.0), position=linear((start, 0.0, 0.0), (-speed, 0.0, 0.0)), radius=radius)
    ahead = unit([[1.0, 0.0, 0.0]])
    for t in (0.0, 0.2, 0.4):
        frame = render(Scene([ball]), ahead, t)
        distance = start - speed * t
        assert frame.depth[0] == pytest.approx(distance - radius, abs=1e-9)
        assert frame.time_to_contact[0] == pytest.approx((distance - radius) / speed, rel=1e-6)
        # its angular size is 2 atan(r / d): a ray at half that angle just grazes it
        half = np.arctan(radius / np.sqrt(distance ** 2 - radius ** 2))
        inside = unit([[np.cos(half * 0.99), np.sin(half * 0.99), 0.0]])
        outside = unit([[np.cos(half * 1.01), np.sin(half * 1.01), 0.0]])
        s, _ = first_hit([ball], np.zeros(3), np.vstack([inside, outside]), t)
        assert np.isfinite(s[0]) and np.isinf(s[1])
