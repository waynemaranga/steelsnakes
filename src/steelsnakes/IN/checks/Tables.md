# Tables (Flattened)

IS 800:2025, draft for comments CED 07 (27869) WC of April 2025. The tables are implemented in `uls.py`; this page
keeps a readable copy, checked against the draft.

## Table 11: Effective length of prismatic compression members

`COMPRESSION_EFFECTIVE_LENGTHS`, `effective_length()`

| End A: Translation | End A: Rotation | End B: Translation | End B: Rotation | Key                 | Effective Length |
| ------------------ | --------------- | ------------------ | --------------- | ------------------- | ---------------- |
| Restrained         | Restrained      | Free               | Free            | `fixed_free`        | $2.0L$           |
| Restrained         | Free            | Free               | Restrained      | `pinned_sway_fixed` | $2.0L$           |
| Restrained         | Free            | Restrained         | Free            | `pinned_pinned`     | $1.0L$           |
| Restrained         | Restrained      | Free               | Restrained      | `fixed_sway_fixed`  | $1.2L$           |
| Restrained         | Restrained      | Restrained         | Free            | `fixed_pinned`      | $0.8L$           |
| Restrained         | Restrained      | Restrained         | Restrained      | `fixed_fixed`       | $0.65L$          |

NOTE: $L$ is the unsupported length of the compression member (14.2.1).

## Table 15: Effective length $L_{LT}$ for simply supported beams

`BEAM_EFFECTIVE_LENGTHS`, `beam_effective_length()`

| Sl No. | Torsional Restraint                           | Warping Restraint                      | Normal Loading | Destabilising Loading |
| ------ | --------------------------------------------- | -------------------------------------- | -------------- | --------------------- |
| (i)    | Fully restrained                              | Both flanges fully restrained          | $0.70L$        | $0.85L$               |
| (ii)   | Fully restrained                              | Only compression flange fully          | $0.75L$        | $0.90L$               |
| (iii)  | Fully restrained                              | Both flanges partially restrained      | $0.80L$        | $0.95L$               |
| (iv)   | Fully restrained                              | Only compression flange partially      | $0.85L$        | $1.00L$               |
| (v)    | Fully restrained                              | No restraint in both flanges           | $1.00L$        | $1.20L$               |
| (vi)   | Partially, by bottom flange support connection | No restraint in both flanges          | $1.0L + 2D$    | $1.2L + 2D$           |
| (vii)  | Partially, by bottom flange bearing support   | No restraint in both flanges           | $1.2L + 2D$    | $1.4L + 2D$           |

NOTES

1. Torsional restraint prevents rotation about the longitudinal axis.
2. Warping restraint prevents rotation of the flange in its plane.
3. $D$ is the overall depth of the beam.
4. In continuous beams, $L$ is the distance between points of inflection, with the restraint conditions there.

## Table 16: Effective length $L_{LT}$ for cantilevers of length $L$

`CANTILEVER_EFFECTIVE_LENGTHS`, `cantilever_effective_length()`; normal / destabilising loading.

| At support                                                         | Top: free   | Lateral restraint to top flange | Torsional restraint | Lateral and torsional |
| ------------------------------------------------------------------ | ----------- | ------------------------------- | ------------------- | --------------------- |
| a) Continuous, with lateral restraint to top flange                | 3.0L / 7.5L | 2.7L / 7.5L                     | 2.4L / 4.5L         | 2.1L / 3.6L           |
| b) Continuous, with partial torsional restraint                    | 2.0L / 5.0L | 1.8L / 5.0L                     | 1.6L / 3.0L         | 1.4L / 2.4L           |
| c) Continuous, with lateral and torsional restraint                | 1.0L / 2.5L | 0.9L / 2.5L                     | 0.8L / 1.5L         | 0.7L / 1.2L           |
| d) Restrained laterally, torsionally and against rotation on plan  | 0.8L / 1.4L | 0.7L / 1.4L                     | 0.6L / 0.6L         | 0.5L / 0.5L           |
