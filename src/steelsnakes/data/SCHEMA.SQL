-- Core section data
CREATE TABLE sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_type TEXT NOT NULL CHECK (section_type IN ('UB', 'UC', 'UBP')),
    designation TEXT NOT NULL,
    serial_size TEXT,
    is_additional BOOLEAN DEFAULT FALSE,
    
    -- Geometric properties
    mass_per_metre REAL CHECK (mass_per_metre > 0),
    h REAL CHECK (h > 0),           -- Overall depth
    b REAL CHECK (b > 0),           -- Overall width  
    tw REAL CHECK (tw > 0),         -- Web thickness
    tf REAL CHECK (tf > 0),         -- Flange thickness
    r REAL CHECK (r >= 0),          -- Root radius
    d REAL CHECK (d > 0),           -- Depth between fillets
    
    -- Ratios
    cw_tw REAL,                     -- Web slenderness
    cf_tf REAL,                     -- Flange slenderness
    
    -- Clearances
    C REAL,                         -- End clearance
    N REAL,                         -- Big Notch
    n REAL,                         -- small notch
    
    -- Surface areas
    surface_area_per_metre REAL,
    surface_area_per_tonne REAL,
    
    -- Second moments of area
    I_yy REAL,                      -- Major axis
    I_zz REAL,                      -- Minor axis
    
    -- Radii of gyration
    i_yy REAL,                      -- Major axis
    i_zz REAL,                      -- Minor axis
    
    -- Section moduli
    W_el_yy REAL,                   -- Elastic, major axis
    W_el_zz REAL,                   -- Elastic, minor axis
    W_pl_yy REAL,                   -- Plastic, major axis
    W_pl_zz REAL,                   -- Plastic, minor axis
    
    -- Buckling and torsion
    U REAL,                         -- Buckling parameter
    X REAL,                         -- Torsional index
    I_w REAL,                       -- Warping constant
    I_t REAL,                       -- Torsional constant
    A REAL,                         -- Cross-sectional area
    
    -- Metadata
    source TEXT,                    -- Data source
    standard TEXT,                  -- BS4, AISC, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(section_type, designation)
);

-- Steel grades/materials
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grade TEXT UNIQUE NOT NULL,     -- S275, S355, S460, etc.
    yield_strength REAL,            -- N/mm²
    ultimate_strength REAL,         -- N/mm²
    elastic_modulus REAL DEFAULT 210000, -- N/mm²
    density REAL DEFAULT 7850,      -- kg/m³
    standard TEXT,                  -- BS EN 10025, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pre-calculated capacities for different steel grades
CREATE TABLE capacities ();

-- Design parameters for different applications
CREATE TABLE design_parameters ();

-- Connection details
CREATE TABLE connections ();

-- Optimization results cache
CREATE TABLE optimization_cache ();

-- User-defined sections (custom sections)
CREATE TABLE custom_sections ();

-- Create indexes for performance
-- CREATE INDEX idx_sections_type_designation ON sections(section_type, designation);
-- CREATE INDEX idx_sections_dimensions ON sections(h, b, mass_per_metre);
-- CREATE INDEX idx_sections_properties ON sections(I_yy, I_zz, W_pl_yy);
-- CREATE INDEX idx_capacities_section_material ON capacities(section_id, material_id);
-- CREATE INDEX idx_optimization_hash ON optimization_cache(criteria_hash);

-- -- Create views for common queries
-- CREATE VIEW section_summary AS
-- SELECT 
--     s.section_type,
--     s.designation,
--     s.mass_per_metre,
--     s.h,
--     s.b,
--     s.A,
--     COUNT(c.id) as capacity_records
-- FROM sections s
-- LEFT JOIN capacities c ON s.id = c.section_id
-- GROUP BY s.id;

-- CREATE VIEW heavy_sections AS
-- SELECT * FROM sections 
-- WHERE mass_per_metre > 100
-- ORDER BY section_type, mass_per_metre DESC;