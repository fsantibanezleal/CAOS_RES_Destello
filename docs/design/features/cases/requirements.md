# Cases, the renderer and the ground truth (U5): requirements

```
R-501  THE ray caster SHALL give the exact first hit of a ray on spheres, planes and the inside of a panoramic
       cylinder or sphere: depth within 1e-9 of the closed form, and the nearer surface where two overlap.
       Gate: tests/test_render.py::test_rays_hit_what_geometry_says

R-502  THE acceptance sampling SHALL weight its 19 rays by the Gaussian of the stated full width, sum to one, render a
       uniform scene as exactly its luminance, and light most the ommatidium that looks at a small bright object.
       Gate: tests/test_render.py::test_acceptance_sampling_is_normalised_and_centred

R-503  THE optic-flow truth SHALL equal the analytic angular velocity: for the fly turning in yaw at omega, every
       ommatidium near the equator sees the scene move at -omega in azimuth, within 0.5%.
       Gate: tests/test_render.py::test_flow_truth_matches_yaw_rotation

R-504  FOR a sphere approaching head-on, THE time-to-contact truth SHALL equal its distance over its speed, and its
       angular size SHALL follow 2 atan(r / d) frame by frame.
       Gate: tests/test_render.py::test_looming_sphere_truth

R-505  EVERY one of the 13 cases SHALL render at least 6 variants for both eyes at 200 frames per second, with a case
       index listing every variant with its parameter, seed, layout and split; every layout SHALL fall wholly in one
       split, and the split sizes SHALL be within 10 points of 60/15/10/15.
       Gate: tests/test_cases.py::test_every_case_has_its_variants_and_clean_splits

R-506  RENDERING a variant twice SHALL give identical bytes.
       Gate: tests/test_cases.py::test_rendering_is_deterministic
```
