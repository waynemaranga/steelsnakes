# ~~ANALYSIS~~ MEMBER CHECKS

NOTE: This is a placeholder for member checks by design/use type. Analysis should be covered in a different module according to Chapter 5 e.g sway imperfection factors et cetera.

<!-- TODO: add an analysis section for Chapter 5 -->
<!-- TODO: put calculation processes docs once and for all... -->
<!-- TODO: use either textbook examples or published sci/steelwork examples -->

## BEAMS

<!-- TODO: just use Arya, notes and design guide :) -->

## COLUMNS

1. Struts
2. Beam-columns
3. Simple columns
4. Column base plate

`N_Ed` - Design axial force
`L_Cr` - Effective length for buckling
`f_y` - Yield strength
`E` - Modulus of elasticity = 210000 N/mm²
`gamma_M0`, `gamma_M1`, `gamma_M2` - Partial safety factors
`pi`
`N_cRd` - Design buckling resistance
`lambda_1` - Non-dimensional slenderness
`lambda_z` - Slenderness ratio
`alpha` - Imperfection factor
`Phi` - Reduction factor
`chi` - Reduction factor for buckling resistance
`A` - Cross-sectional area
`N_bRd` - Design buckling resistance for struts

## Testing table 6.2

| Section Type | h/b > 1.2 | h/b <= 1.2 | tf <= 40mm | 40mm < tf <= 100mm | tf <= 100mm | tf > 100mm | hot-finished | cold-formed | y-y axis | z-z axis | S235 etc | S460 |
| ------------ | --------- | ---------- | ---------- | ------------------ | ----------- | ---------- | ------------ | ----------- | -------- | -------- | -------- | ---- |
| Rolled I & H | TRUE      | FALSE      | TRUE       | FALSE              | VOID        | VOID       | N-A          | N-A         | TRUE     | FALSE    | a        | a0   |
| Rolled I & H | TRUE      | FALSE      | TRUE       | FALSE              | VOID        | VOID       | N-A          | N-A         | FALSE    | TRUE     | b        | a0   |
| Rolled I & H | TRUE      | FALSE      | FALSE      | TRUE               | VOID        | VOID       | N-A          | N-A         | TRUE     | FALSE    | b        | a    |
| Rolled I & H | TRUE      | FALSE      | FALSE      | TRUE               | VOID        | VOID       | N-A          | N-A         | FALSE    | TRUE     | c        | a    |
| Rolled I & H | FALSE     | TRUE       | VOID       | VOID               | TRUE        | FALSE      | N-A          | N-A         | TRUE     | FALSE    | b        | a    |
| Rolled I & H | FALSE     | TRUE       | VOID       | VOID               | TRUE        | FALSE      | N-A          | N-A         | FALSE    | TRUE     | c        | a    |
| Rolled I & H | FALSE     | TRUE       | VOID       | VOID               | FALSE       | TRUE       | N-A          | N-A         | TRUE     | FALSE    | d        | c    |
| Rolled I & H | FALSE     | TRUE       | VOID       | VOID               | FALSE       | TRUE       | N-A          | N-A         | FALSE    | TRUE     | d        | c    |
| Hollow       | N-A       | N-A        | N-A        | N-A                | N-A         | N-A        | TRUE         | FALSE       | TRUE     | TRUE     | a        | a0   |
| Hollow       | N-A       | N-A        | N-A        | N-A                | N-A         | N-A        | FALSE        | TRUE        | TRUE     | TRUE     | a        | a0   |
| Channels     | N-A       | N-A        | N-A        | N-A                | N-A         | N-A        | N-A          | N-A         | TRUE     | TRUE     | c        | c    |
| Tees         | N-A       | N-A        | N-A        | N-A                | N-A         | N-A        | N-A          | N-A         | TRUE     | TRUE     | c        | c    |
| Angles       | N-A       | N-A        | N-A        | N-A                | N-A         | N-A        | N-A          | N-A         | TRUE     | TRUE     | b        | b    |

TRUE = condition satisfied, FALSE = condition not satisfied but satisfiable in another case, VOID = condition not applicable in this row i.e voided by other conditions, NULL = section type not applicable
N-A = not applicable to this section
Welded sections are not included in this table

## Testing table 5.2

### Sheet 1 - Internal compression parts

| Class | Bending              | Compression          | Bending + Compression       |     |
| ----- | -------------------- | -------------------- | --------------------------- | --- |
| 1     | $c/t \le 72\epsilon$ | $c/t \le 33\epsilon$ | $c/t\le 72\epsilon$ for ... |     |

<!-- TODO: complete and tabulate for programmning.. -->
