# Indian Standard is mostly UK/EU based but with a bit of US influence e.g tying all checks to a named limit state.
# Can see UK influence on bending compressive stress for buckling # NOTE: see if IS 800:2025 will upgrade this
# After breakdown from guide book, implement actual equations from copy of code; consider release of IS 800:2025 later in the year to supersede IS 800:2007

# Section 6: Tension
# 6.2 Design strength due to yielding of gross section
# 6.3 Design strength due to rupture of critical section 
# 6.3.1 Plates
# 6.3.2 Threaded rods
# 6.3.3 Single Angles
# 6.4 Design strength due to block shear
# 6.4.1 Bolted connections
# 6.4.2 Welded connections

# -----------------------------------------------------------------------------
# Section 7: Compression
# TODO: Add clauses in docs like 7.1.1
# 7.1.2 Design compressive strength: Pd = Ae*fcd;
# Ae = effective sectional area per 7.3.2; fcd = design compressive strength per 7.1.2.1
# 7.1.2.1 fcd - Design compressive stress of axially loaded compression members
# fcd = (fy*gamma_M0)/(phi + [phi^2 - lambda^2]^0.5) = chi*fy/gamma_M0 but <= fy/gamma_M0
# phi = 0.5[1 + alpha*(lambda - 0.2) + lambda^2]; alpha = imperfection factor from Table 7; 
# chi: stress reduction factor = 1/(phi + [phi^2 - lambda^2]^0.5); chi given for diff. buckling class, slenderness ratios and yield stress;
# lambda: nondimensional effective slenderness ratio = sqrt(fy/fcc) = sqrt( fy*(K*L/r)^2 / (pi^2*E) )
# fcc: Euler buckling stress = (pi^2*E)/(K*L/r)^2
# KL/r: effective slenderness ratio; r: radius of gyration; K: effective length factor; L: unsupported length
# TODO: implement buckling curves from EU/UK
# 7.2 Effective length of compression members: #TODO: add notes to docs
# 7.2.2 Effective length KL: calc. from Table 11
# 7.2.3
# 7.2.4 Compression members in trusses
# 7.3 Design details 
# 7.3.1 Thickness of plate elements
# 7.3.2 Effective sectional area Ae
# 7.3.3 Eccentricity for stanchions and columns
# 7.3.4 Splices
# 7.4 Column bases
# 7.5 Angle struts
# 7.5.1 Single angle struts
# 7.5.1.1 Concentric loading
# 7.5.1.2 Loaded through one leg
# 7.5.2 Double angle struts
# 7.5.3 Continuous members
# 7.6 Laced columns
# 7.7 Battened columns

# -----------------------------------------------------------------------------
# Section 8: Bending
# 8.1
# 8.1.1 Effective span of beams
# 8.2 Design strength in bending/flexure: M<=Md; Md from 8.2.1.2    
# 8.2.1 Laterally supported beams
# 8.2.1.2 Md when factored V <= 0.6*Vd
# Md = beta_b*Zp*fy/gamma_M0; beta_b = 1.0 for plastic & compact sections and Ze/Zp for semi-compact sections; Zp, Ze: plastic, elastic section modulus, fy: yield stress; gamma_M0: partial safety factor for material strength = 1.10
# Md < 1.2*Ze*fy/gamma_M0 for simply-supported beams and Md < 1.5*Ze*fy/gamma_M0 for cantilever beams to prevent irreversible deflection under service loads
# 8.2.1.3 Md when factored V > 0.6*Vd
# Md = Mdv per Section 9: Combined Forces (Shear+Bending)
# 8.2.1.4 Holes in tension zone
# 8.2.1.5 Shear lag effects # TODO: implement; find out if necessary for standard sections
# 8.2.2 Laterally unsupported beams
# NOTE: TODO: add notes for when not/to check separately for LTB resistance
# Design bending strength for   laterally unsupported beams as governed by lateral-torsional buckling:
# Md = beta_b*Zp*fbd; beta_b = 1.0 for plastic & compact sections and Ze/Zp for semi-compact sections; fbd: design bending compressive stress 
# fbd = chi_LT*fy/gamma_M1; chi_LT: bending stress reduction factor for LTB;
# chi_LT: 1/[phi_LT + (phi_LT^2 - lambda_LT^2)^0.5] but chi_LT<=1.0 ; phi_LT = 0.5[1 + alpha_LT*(lambda_LT - 0.2) + lambda_LT^2];
# alpha: imperfection parameter = 0.21 for rolled sections and 0.49 for welded sections; 
# lambda_LT: nondimensional slenderness ratio for LTB = sqrt(fy/fcrb); fcrb: extreme fibre bending compressive stress corresponding to elastic lateral buckling moment
# lambda_LT = sqrt([beta_b*Zp*fy/Mcr]) <= sqrt([1.2*Ze*fy/Mcr]); Mcr: elastic lateral buckling moment
# 8.2.2.1 Elastic lateral buckling moment Mcr
# -> Mcr for simply-supported, prismatic members with symmetric x-section,
# Mcr = beta_b*Zp*fcrb = [(pi^2*E*Iy)/L_LT^2 * (G*It + (pi^2*E*Iw)/L_LT^2)]^0.5
# -> approximate fcrb in above equation for non-slender rolled steel sections,
# fcrb = (1.1*pi^2*E)/(L_LT/ry)^2 * [1 + 0.05(L_LT/ry / hf/tf)^2]^0.5
# -> Simplified Mcr for standard rolled I-sections and welded doubly-symmetric I-sections
# Mcr = (pi^2*E*Iy*hf)/(2*L_LT^2) * [1 + 0.05(L_LT/ry / hf/tf)^2]^0.5; It: torsional contant
# 8.3 Effective length of for lateral-torsional buckling L_LT
# TODO: implement table 15 and include notes; make docs site useful + examples per code; add examples with notebooks and handcalcs over time; install steelsnakes and handcalcs and use;
# TODO: implement table 16; clear UK/BS 5950 influence
# TODO: in steelsnakes[extras], implemet simple fastapi section browser and test/implement search and fuzzy search; should include sqlite

# 8.4 Shear: factored design shear force V <= Vd; Vd: design shear strength;
# Nominal shear resistance Vn may be governed by plastic shear or strength of web in shear buckling
# 8.4.1 Nominal plastic shear resistance Vn
# Vp = Av*fyw/sqrt(3); Av: shear area; fyw: yield strength of web
# 8.4.1.1 Shear area Av
# I- and channel sections: Major axis: h*tw (is d*tw for welded), Minor axis: 2*b*tf # TODO: though not implementing welded, make functions before 1.0.0 agnostic i.e take **kwargs or section and run.
# RHS of uniform thickness: Load // depth(h): A*h/(b+h); Load // width(b): A*b/(b+h)
# CHS of uniform thickness: 2*A/pi
# Plates and solid bars: A
# TODO: find angle calc for shear area
# NOTE: check & implement condition for fastener holes... Avn >= (fy/fu)*(gamma_M1/gamma_M0)*Av/0.9
# 8.4.2 Resistance to shear buckling
# 8.4.2.1 Conditions to verify: d/tw > 67*epsilon for web without stiffeners; > 67*epsilon*[Kv/5.35]^0.5 for web with stiffeners; 
# epsilon = sqrt(250/fy); Kv: shear buckling coefficient 
# 8.4.2.2 Shear buckling design methods
# 8.4.2.2(a) Simple post-critical method
# 8.4.2.2(b) Tension field method

# 8.5 Stiffened web panels
# 8.5.1 End panels design
# 8.5.2 End panels design using tension field action
# 8.5.3 Anchor forces
# 8.5.4 Panels with opening

# 8.6 Design of beams with plate girders and solid webs
# 8.7 Stiffener Design

# -----------------------------------------------------------------------------
# Section 9: Combined Forces (Shear+Bending; Axial+Bending)
# 9.2 Combined shear and bending
# 9.2.1 When factored shear force V <= 0.6*Vd from 8.4, take Md from 8.2
# 9.2.2 When factored shear force V > 0.6*Vd from 8.4, factored Md < Mdv
# 9.2.2(a) Mdv for plastic & compact sections
# Mdv = Md - beta*(Md - Mfd) <= 1.2*Ze*fy/gamma_M0; beta = (2V/Vd - 1)^2
# Md: plastic moment disregarding high shear (8.2.1.2) but considering web buckling (8.2.1.1)
# V: factored applied shear force governed by web yielding or web buckling
# Vd: design shear strength governed by web yielding or web buckling (8.4.1 or 8.4.2)
# Mfd: plastic design strength of area of x-section excluding shear area and considering gamma_M0
# Ze: elastic section modulus of entire x-section
# 9.2.2(b) Mdv for semi-compact sections
# Mdv = Ze*fy/gamma_M0 

# 9.3 Combined axial force and bending
# 9.3.1 Section strength
# 9.3.1.1 Plastic & compact sections
# 9.3.1.2 Approx. Mndy and Mndz for plastic & compact sections without bolt holes
# 9.3.1.3 Semi-compact sections

# 9.3.2 Overall member strength
# 9.3.2.1 Bending and axial tension
# 9.3.2.2 Bending and axial compression

# -----------------------------------------------------------------------------
# Section 10: Connections
# 10.2 Location and details
# 10.2.1 Clearances for holes
# 10.2.2 Minimum spacing
# 10.2.3 Maximum spacing
# 10.2.4 Edge and End distances
# 10.2.5 Tacking
# 10.2.6 Countersunk heads

# 10.3 Bearing type bolts
# 10.4 Friction grip type bolts
# 10.5 Welds and Welding
# 10.6 Connection design
# 10.7 Minimum design action

# -----------------------------------------------------------------------------
# Section 11: Working Stress Design [WILL NOT IMPLEMENT]