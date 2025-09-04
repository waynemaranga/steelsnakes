# Cl. 6.3 Buckling

# Cl. 6.3.1 Uniform members in compression
# Cl. 6.3.1.1(3) - design buckling resistance for Class 1, 2 & 3 cross-sections N_bRd
# eq. 6.47 ; chi (χ) is the reduction factor for the relevant buckling mode
# N_bRd = chi*A*f_y/gamma_M1

# Cl. 6.3.1.2 Buckling curves
# eq. 6.49 chi = 1/(phi + sqrt(phi^2 - lambda_bar^2)) <= 1.0; 
# and phi = 0.5[1 + alpha*(lambda_bar - 0.2) + lambda_bar^2] ; lambda_bar = sqrt(A*f_y/N_cr) for Class 1, 2 & 3 cross-sections
# alpha (!= alpha in biaxial bending) is imperfection factor # TODO: IMPORTANT: delineate shared values/variables like alpha
# Ncr is elastic critical force for given buckling mode
# alpha is read off from Table 6.1 corresponding to buckling curve which is read off from Table 6.2
# TODO: table 6.1 is simple dictionary: {'curve': alpha} = {'a0': 0.13, 'a': 0.21, 'b': 0.34, 'c': 0.49, 'd': 0.76}
# TODO: implement Table 6.2; specify also rolled/welded. See if table is flattenable; check Members.md

# Cl. 6.3.1.3 Slenderness for flexural buckling
# eq. 6.50 lambda_bar for Class 1, 2 & 3 cross-sections
# lambda_bar = sqrt(A*f_y/N_cr) = Lcr/i * 1/lambda_1; Lcr is critical buckling length; i is radius of gyration about relevant axis
# lambda_1 = pi*sqrt(E/f_y) = 93.9*epsilon; epsilon = sqrt(235/f_y)

# Cl. 6.3.1.4 Slenderness for torsional and torsional-flexural buckling
# eq. 6.52 lambdaT_bar for Class 1, 2 & 3 cross-sections
# lambdaT_bar = sqrt(A*f_y/N_cr); N_cr = N_crTF but N_cr < N_crT; N_crT: elastic torsional buckling force; N_crTF: elastic torsional-flexural buckling force

# --------------------------------------------------------------------------------------
# NOTE: TODO: Consult  NCCI SN002 (SCI, 2005a), NCCI SN009 (SCI, 2005c). and Designer's Guide/personal notes for this
# Have Eurocde implementation strictly follow EN 1993-1-1:2005 + A1:2014 and UK implementation follow NCCI SN002 or UK NA et cetera.
# Cl. 6.3.2 Uniform members in bending
# Cl. 6.3.2.1 Buckling resistance
# eq. 6.54 M_Ed / M_bRd <= 1.0; 
# eq. 6.55 M_bRd: Design buckling resistance moment of a laterally unrestrained beam 
# M_bRd = chi_LT * Wpl_y * f_y / gamma_M1 for Class 1 & 2 cross-sections
# M_bRd = chi_LT * Wel_y * f_y / gamma_M1 for Class 3 cross-sections; chi_LT is reduction factor for lateral-torsional buckling;
# TODO: bright idea! implement HTML with/without server/fastapi to render LaTeX calculations and tables with MathJax! (or maybe matplotlib can do it?) # https://matplotlib.org/stable/users/explain/text/usetex.html

# Cl. 6.3.2.2 LTB - General Case
# Cl. 6.3.2.3 LTB curves for rolled sections or equivalent welded sections
# TODO: document and implement carefully at the same time as UK considering appendices and national annexes...