# Cases

Thirteen cases in six categories. Every case varies one physical parameter over at least six values, and every variant
is rendered for both eyes with exact ground truth (depth along each ommatidium's ray, object masks, optic flow, time to
contact). Splits for the learned readouts group by scene layout and stimulus seed, so no layout or seed reaches both
train and test. One page per case is added to `cases/` when the case is built.

| Category | Case | Varied parameter | Why it exists |
|---|---|---|---|
| Motion primitives | C01 gratings | temporal frequency (8 directions each) | direction selectivity, optomotor drive |
| | C02 moving edges | speed (ON and OFF, 8 directions) | the ON and OFF pathways, T4 versus T5 |
| | C03 flashes | contrast | polarity of the lamina and medulla |
| Looming and collision | C04 looming disc | size-to-speed ratio l/v | LPLC2 and LC4 to the giant fibre, the escape |
| | C05 receding disc | l/v | negative control for C04 |
| | C06 wall approach in flight | approach speed | time to contact, depth |
| Self-motion | C07 yaw rotation | angular velocity | optomotor response; depth is unobservable (a control for the parallax readouts) |
| | C08 corridor translation | forward speed | depth from parallax |
| Objects and figure-ground | C09 small target | target size | the small-object channel (LC11) |
| | C10 figure over ground | relative speed | segmentation by relative motion |
| Social and natural | C11 rival fly | trajectory | LC10 and courtship pursuit, a known gap of the raw wiring |
| | C12 natural flights | scene and path | everything together, on natural image statistics |
| Controls | C13 dark and static | luminance, duration | spontaneous activity; nothing should move |
