# Processing Range Capability

## ADDED Requirements

### Requirement: X-Range Selection for Focused Analysis

The system SHALL allow users to limit spectral processing (spike removal, baseline correction, fitting) to a specified X-axis range, enabling precise analysis of spectral regions without interference from noisy edges or irrelevant features.

**Controls (in Pre-process tab):**
- Checkbox: "Limit to X range" (default: unchecked)
- Numeric inputs: `X min`, `X max` (units auto-set by mode: cm⁻¹ or nm)
- Inputs auto-populated with full data range on file load

**Behavior:**
- When unchecked: All operations use full spectrum (v2.0 behavior)
- When checked: Processing limited to `[X min, X max]` range as specified below
- Range settings saved per-file in session state and project JSON

#### Scenario: Enable X-range limiting for Raman spectrum

- **WHEN** user loads a Raman spectrum with X from -680 to 3200 cm⁻¹
- **AND** checks "Limit to X range"
- **AND** sets X min = 1000, X max = 2000
- **THEN** processing uses only data points where 1000 ≤ X ≤ 2000
- **AND** plots show full spectrum with active range visually highlighted

#### Scenario: Disable X-range limiting (full spectrum mode)

- **WHEN** user unchecks "Limit to X range"
- **THEN** all processing operations use full spectrum
- **AND** X min/max inputs are greyed out (disabled)
- **AND** no visual range indicators displayed in plots

#### Scenario: Auto-populate range from data

- **WHEN** user loads new file `sample.txt` with X from 800 to 900 nm
- **THEN** X min input is pre-filled with 800
- **AND** X max input is pre-filled with 900
- **AND** checkbox remains unchecked (user must explicitly enable)

### Requirement: Range-Limited Spike Removal

When X-range limiting is enabled, the system SHALL detect cosmic ray spikes on the full spectrum for consistent diagnostics, but only replace spikes within the specified range.

#### Scenario: Detect spikes on full spectrum, replace only in range

- **WHEN** X-range is limited to [1200, 1800] cm⁻¹
- **AND** spectrum has spikes at 1000, 1500, and 2500 cm⁻¹
- **THEN** system detects all 3 spikes
- **AND** replaces spike at 1500 (within range) with local median
- **AND** leaves spikes at 1000 and 2500 unmodified (outside range)
- **AND** spike count message shows "3 spikes detected, 1 replaced"

#### Scenario: Full spectrum spike removal when range disabled

- **WHEN** X-range limiting is unchecked
- **AND** user clicks "Auto Remove Spikes"
- **THEN** system detects and replaces all spikes across full spectrum

### Requirement: Range-Limited Baseline Correction

When X-range limiting is enabled, the system SHALL compute baseline using only data points within the specified range and correct Y values only in that range.

#### Scenario: Polynomial baseline on limited range

- **WHEN** X-range is set to [1400, 1600] cm⁻¹
- **AND** user selects polynomial baseline (degree 2)
- **THEN** system fits polynomial using only X, Y data where 1400 ≤ X ≤ 1600
- **AND** subtracts baseline only for points in that range
- **AND** Y values outside [1400, 1600] remain unprocessed

#### Scenario: ALS baseline respects range boundaries

- **WHEN** X-range is limited to [850, 900] nm
- **AND** user applies ALS baseline (λ=10⁴, p=0.001)
- **THEN** ALS algorithm uses only data points in [850, 900] nm
- **AND** baseline-corrected Y computed only for that range
- **AND** out-of-range data displayed as greyed-out in plots

### Requirement: Range-Limited Fitting

When X-range limiting is enabled, the system SHALL provide a checkbox in the Fit Model tab to control whether peak fitting uses only the limited range or the full spectrum.

**Controls (in Fit Model tab):**
- Checkbox: "Fit only within X range" (default: ON when range limiting enabled)
- When ON: Fitting uses only data points within `[X min, X max]`
- When OFF: Fitting uses full spectrum (including unprocessed regions)

#### Scenario: Fit peaks within limited range only

- **WHEN** X-range is limited to [1200, 1800] cm⁻¹ in Pre-process tab
- **AND** "Fit only within X range" is checked in Fit Model tab
- **AND** user adds 2 peaks and runs fit
- **THEN** lmfit uses only data where 1200 ≤ X ≤ 1800
- **AND** fitted curves displayed only in active range
- **AND** residuals computed only for active range

#### Scenario: Fit on full spectrum despite range limiting

- **WHEN** X-range limiting is enabled in Pre-process
- **AND** "Fit only within X range" is unchecked in Fit Model tab
- **THEN** fitting uses full spectrum data (including unprocessed regions)
- **AND** warning message displayed: "Fitting includes unprocessed data outside range"

#### Scenario: Checkbox hidden when range limiting disabled

- **WHEN** "Limit to X range" is unchecked in Pre-process tab
- **THEN** "Fit only within X range" checkbox is hidden in Fit Model tab
- **AND** fitting always uses full spectrum

### Requirement: Visual Range Indicators

The system SHALL display clear visual indicators in all plots to mark the active processing range boundaries and distinguish in-range vs. out-of-range data.

**Visual Elements:**
- Vertical dashed lines at X min and X max boundaries
- Data outside range displayed at 30% opacity (greyed-out)
- Active range data displayed at 100% opacity (normal)
- Optional shaded region or color distinction

#### Scenario: Boundary lines at range limits

- **WHEN** X-range is set to [1000, 2000] cm⁻¹
- **THEN** plots display vertical dashed line at X = 1000
- **AND** vertical dashed line at X = 2000
- **AND** lines span full Y-axis height

#### Scenario: Out-of-range data greyed out

- **WHEN** X-range is limited to [1400, 1600] cm⁻¹
- **THEN** data points where X < 1400 displayed at 30% opacity
- **AND** data points where X > 1600 displayed at 30% opacity
- **AND** data points where 1400 ≤ X ≤ 1600 displayed at 100% opacity

#### Scenario: Visual indicators persist across tabs

- **WHEN** X-range limiting is enabled in Pre-process tab
- **THEN** boundary lines and opacity styling appear in Pre-process plot
- **AND** same indicators appear in Fit Model plot
- **AND** same indicators appear in Visualize & Export composite plot

### Requirement: Per-File Range State Persistence

The system SHALL save X-range settings independently for each file in session state and project JSON, allowing different analysis ranges for different spectra.

#### Scenario: Different ranges for different files

- **WHEN** user sets File A range to [1200, 1800] cm⁻¹
- **AND** sets File B range to [800, 900] nm
- **AND** switches back to File A
- **THEN** File A range settings [1200, 1800] are restored
- **AND** processing uses File A's range

#### Scenario: Project JSON stores per-file ranges

- **WHEN** user saves project with 3 files having different X-ranges
- **THEN** JSON contains per-file entries with `x_range_enabled`, `x_min`, `x_max` fields
- **AND** reloading project restores each file's range settings
- **AND** visual indicators appear correctly for each file

### Requirement: Export Metadata for X-Range

The system SHALL include X-range settings in exported Master CSV to document analysis scope for each spectrum.

**New CSV Columns:**
- `x_range_limited` (TRUE/FALSE)
- `x_min` (numeric or empty if not limited)
- `x_max` (numeric or empty if not limited)

#### Scenario: CSV export includes range metadata

- **WHEN** File A has range limiting enabled [1000, 2000]
- **AND** File B has range limiting disabled
- **AND** user exports Master CSV
- **THEN** File A rows show `x_range_limited: TRUE, x_min: 1000, x_max: 2000`
- **AND** File B rows show `x_range_limited: FALSE, x_min: , x_max: `

#### Scenario: Peak parameters reflect limited range analysis

- **WHEN** peak fitting performed on range [1400, 1600] cm⁻¹
- **AND** fitted peak center is 1520 cm⁻¹
- **THEN** CSV row includes center = 1520
- **AND** same row shows x_min: 1400, x_max: 1600
- **AND** user can correlate fitted parameters with analysis scope

### Requirement: Validation and Error Handling

The system SHALL validate X-range inputs and provide clear feedback for invalid range specifications.

#### Scenario: X min greater than X max

- **WHEN** user sets X min = 2000, X max = 1000
- **THEN** system displays error: "X min must be less than X max"
- **AND** processing is blocked until corrected
- **AND** inputs highlighted in red

#### Scenario: Range outside data bounds

- **WHEN** spectrum has X from 800 to 1800 cm⁻¹
- **AND** user sets X min = 2000, X max = 2500
- **THEN** system displays warning: "Range is outside data bounds"
- **AND** processing proceeds but uses no data points (empty range)
- **AND** plot shows no active range (all data greyed out)

#### Scenario: Valid partial overlap range

- **WHEN** spectrum has X from 1000 to 2000 cm⁻¹
- **AND** user sets X min = 1800, X max = 2500
- **THEN** system uses data points in [1800, 2000] (valid overlap)
- **AND** no error displayed
- **AND** visual indicators show [1800, 2000] as active range
