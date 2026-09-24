# Cases, the renderer and the ground truth (U5): design

Written 2026-09-24, before the code of this unit.

## What this unit produces

Every case of the SDD (section 7), every variant, both eyes: what each ommatidium sees, frame by frame, and the exact
truth about it. It is the only source of visual input for every engine and readout, and the only source of truth for
every metric.

## The renderer: analytic ray casting on the fly's own eyes

Scenes are built from primitives whose intersection with a ray has a closed form: spheres, ellipsoids (the rival
fly), planes (bounded or not), and vertical cylinders (tree trunks, and seen from inside, panoramic backgrounds). Each primitive carries a pattern
(uniform, sinusoidal grating, square wave, a seeded 1/f texture) that maps the hit point to a luminance in [0, 1].
The fly's head is at the origin of the body frame (x forward, y left, z up, the frame of `flycns.eyes`); its pose
over time (position and heading) is part of the case. Objects move on stated trajectories.

**What an ommatidium sees.** For ommatidium ``i`` with direction ``d_i`` (from `flycns.eyes`, both MaleCNS eyes), the
luminance is the acceptance-weighted average over a fixed set of sample rays around ``d_i``: 19 directions, the centre
and rings of 6 and 12 at one and two sigma of the Gaussian acceptance (full width at half maximum 8.23 degrees),
weighted by the Gaussian. The same set is used for every ommatidium and frame, so rendering is deterministic.

**The truth, per ommatidium and frame, from the central ray:**

- depth: the distance along the ray to the first surface (infinite for the sky or the background);
- the object: which primitive the ray hits (the figure, the target, the rival fly, the background);
- optic flow: the angular velocity of the hit point in the eye's local frame (azimuth, elevation, degrees per
  second), from the scene's motion over the frame, computed from the point's positions at t - dt/2 and t + dt/2;
- time to contact for an approaching object: its distance over its closing speed along the ray.

The frame rate is the graded engine's step, 200 frames per second (5 ms), so every engine reads the frames as they
are rendered.

**E3's input.** E3 runs flyvis's own network per eye on its 721-column lattice; the same scene is rendered at the
lattice columns' directions, which `flycns.mapped` places in each eye's local frame.

**V8's input.** The monocular depth reference sees a full-resolution image: each eye's view rendered as a
518 x 518 azimuthal-equidistant image around the eye's centre direction, 180 degrees wide, with its depth, at a
subset of frames. It is labelled as not the fly. Those images are made by the readout unit (V8), with this
renderer, not by the dataset stage.

## The cases

Thirteen cases in six categories (SDD section 7). Each varies one physical parameter over at least six values; the
other parameters are fixed per case and stated in the case table. Durations: 1 s grey lead-in is part of every
engine's steady state, not of the case; each case lasts 0.6 to 1.5 s of stimulus.

| Case | Scene | Varied parameter (values) |
|---|---|---|
| C01 gratings | a sinusoidal grating on a cylinder around the fly, drifting | temporal frequency 0.5, 1, 2, 4, 8, 16 Hz (8 directions each) |
| C02 moving edges | a full-field ON or OFF edge | speed 30, 60, 90, 120, 180, 240 deg/s (8 directions, both polarities) |
| C03 flashes | a full-field step from grey | contrast -1, -0.6, -0.3, 0.3, 0.6, 1 |
| C04 looming disc | a dark sphere approaching head-on at constant speed | size-to-speed ratio l/v 10, 20, 40, 60, 80, 120 ms |
| C05 receding disc | the same sphere moving away | l/v 10, 20, 40, 60, 80, 120 ms |
| C06 wall approach | a textured wall ahead, the fly flying toward it | speed 0.1, 0.2, 0.3, 0.5, 0.7, 1.0 m/s |
| C07 yaw rotation | the fly turning in a textured cylinder | angular velocity 30, 60, 120, 240, 360, 500 deg/s |
| C08 corridor | the fly flying down a textured corridor | speed 0.1, 0.2, 0.3, 0.5, 0.7, 1.0 m/s |
| C09 small target | a small dark sphere crossing in front | angular size 2, 3, 5, 8, 12, 20 deg |
| C10 figure over ground | a textured square moving against textured ground | relative speed 10, 30, 60, 90, 120, 180 deg/s |
| C11 rival fly | a fly-sized ellipsoid on a courtship-like path | path (6 seeded trajectories) |
| C12 natural flights | textured trees and ground, a seeded flight path | scene and path (6 seeds) |
| C13 dark and static | uniform or static scenes | luminance 0, 0.1, 0.3, 0.5, 0.7, 1 |

## Splits

Learned readouts (V6, V7) train on the train split only. A split groups by what could leak: the scene layout (the
texture seed of cases with textures) and the stimulus seed. Each variant carries its layout and seed, and a layout
is assigned wholly to one split: 60% train, 15% validation, 10% calibration, 15% test, by a seeded hash of the layout
id. No layout or seed reaches two splits.

## Output

One directory per case and variant in the compiled style (a manifest with the SHA-256 of every array): intensity per
frame and column for both eyes (uint16, luminance times 65535: the compiled format has no float16), E3's lattice
intensities (frames x 2 x 721), the truth (depth, object id, optic flow, time to contact), the case's parameters,
seed, layout and split. A case index lists every variant.
