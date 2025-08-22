# TODO

- [ ] In SQLite, columns are being renamed automatically, and aliases have not been used in this project
- [ ] Implement aliases again when double checking the modules
- [ ] Use actual names in SQLite, and revise api to work between aliases
- [ ] Parse/Wrangle and document how non-preloaded bolts were done
- [ ] Document wrangling of American sections
- [ ] Reading Australian sections from <http://www.steelweb.info/> will make a very interesting webscraping project. In absence of spreadsheets, perform this in a separate repository and link to it.
- [ ] Do similar linking of datapreps/scraping of UK and US
- [ ] Scraping SkyCiv's <beamdimensions.com> for other sections seems like a good idea
- [ ] Once all steel sections are done, start normalising dimensional properties across sections:
  - [ ] match depths to depths, flange widths to flange widths,
  - [ ] also match section areas, mass per unit length, section moduli, moments of inertia, radii of gyration, etc.
  - [ ] This will allow searching for sections across types, e.g. "find me a section with depth 300mm, mass 20kg/m, and Iyy > 50000 cm4"
- [ ]Try use unit conversion libraries like Pint or Pydantic's built-in units or forallpeople and SI
- [ ] To beat SQLite's case (insensitivity) add units to the column names, e.g. h_mm, b_mm, t_mm, A_cm2, Iyy_cm4, etc.