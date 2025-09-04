# Tables (Flattened)

## Table 11: Effective length of prismatic compression members

<!-- TODO: Implement JSON and lookup -->
<!-- TODO: Double check values with actual code -->

| End A: Translation | End A: Rotation | End B: Translation | End B: Rotation | Schem. Rep | Effective Length |
| ------------------ | --------------- | ------------------ | --------------- | ---------- | ---------------- |
| Restrained         | Restrained      | Free               | Free            | 1          | $2.0L$           |
| Free               | Restrained      | Free               | Restrained      | 2          | $2.0L$           |
| Restrained         | Free            | Restrained         | Free            | 3          | $1.0L$           |
| Restrained         | Restrained      | Free               | Restrained      | 4          | $1.2L$           |
| Restrained         | Restrained      | Restrained         | Free            | 5          | $0.8L$           |
| Restrained         | Restrained      | Restrained         | Free            | 6          | $0.65L$          |

## Table 15: Effective length $L_{LT}$ for simply-supported beams

| SI No. | Torsional Restraint                           | Warping Restraint            | Normal Loading | Destabilising Loading |
| ------ | --------------------------------------------- | ---------------------------- | -------------- | --------------------- |
| (i)    | Fully restrained                              | Both flanges fully           | $0.70L$        | $0.85L$               |
| (ii)   | Fully restrained                              | Compression flange fully     | $0.75L$        | $0.90L$               |
| (iii)  | Fully restrained                              | Free                         | $0.80L$        | $0.95L$               |
| (iv)   | Fully restrained                              | Compression flange partially | $0.85L$        | $1.00L$               |
| (v)    | Fully restrained                              | Not restrained both flanges  | $1.00L$        | $1.20L$               |
| (vi)   | Bottom flange partially by support connection | Not restrained both flanges  | $1.0L + 2D$    | $1.2L + 2D$           |
| (vii)  | Bottom flange partially by bearing support    | Not restrained both flanges  | $1.2L + 2D$    | $1.4L + 2D$           |

NOTES

1. Torsional restraint prevents rotation about the longitudinal axis.
2. Warping restraint prevents rotation of the flange in its plane.
3. $D$ is the overall depth of the beam.
