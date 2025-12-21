# Plot Visualization Specification

## ADDED Requirements

### Requirement: Unified Multi-Layer Plot

The application SHALL display a single Plotly plot that shows all processing stages (raw, de-spiked, baseline-corrected, fit) as toggleable layers.

#### Scenario: Single plot for all stages
- **WHEN** a spectrum file is loaded and processed
- **THEN** all processing layers render on the same Plotly figure
- **AND** the plot maintains consistent zoom and pan state across layer changes

#### Scenario: Available plot layers
- **WHEN** a spectrum has been processed through multiple stages
- **THEN** the plot can display up to 7 layer types: Raw data, De-spiked data, Baseline preview (red dashed), Corrected preview (green), Baseline-corrected data, Fit total curve, Individual fit components

### Requirement: Layer Visibility Controls

Users SHALL be able to toggle the visibility of plot layers via checkboxes in the right panel.

#### Scenario: View options checkboxes
- **WHEN** a user views the right panel "View options" subsection
- **THEN** checkboxes are displayed for: Show Raw, Show De-spiked, Show Baseline-corrected, Show Fit, Show Components

#### Scenario: Checkbox toggle updates plot
- **WHEN** a user unchecks "Show Raw"
- **THEN** the raw data trace immediately disappears from the plot
- **AND** the plot does not recompute or reload (Plotly visibility toggle only)

#### Scenario: Independent layer visibility
- **WHEN** multiple layers exist (e.g., de-spiked, baseline-corrected, fit)
- **THEN** each layer can be shown or hidden independently
- **AND** at least one layer must remain visible (no fully blank plot)

### Requirement: Default Layer Visibility

The plot SHALL automatically update default layer visibility based on the most recent processing step.

#### Scenario: Initial load shows raw
- **WHEN** a spectrum file is first loaded
- **THEN** only the "Raw data" layer is visible by default

#### Scenario: After despike shows de-spiked
- **WHEN** the despike step completes successfully
- **THEN** the "De-spiked" layer becomes visible by default
- **AND** the "Raw data" layer becomes hidden by default (but remains toggleable)

#### Scenario: After baseline shows corrected
- **WHEN** the baseline correction step completes successfully
- **THEN** the "Baseline-corrected" layer becomes visible by default
- **AND** previous layers (Raw, De-spiked) become hidden by default

#### Scenario: After fit shows corrected plus fit
- **WHEN** the peak fitting step completes successfully
- **THEN** both "Baseline-corrected" and "Fit total curve" layers are visible by default
- **AND** individual components remain hidden by default

### Requirement: Real-Time Baseline Preview Integration

The unified plot SHALL display real-time baseline preview overlays (from v2.1) using red dashed and green solid traces.

#### Scenario: Preview overlay during baseline adjustment
- **WHEN** a user adjusts baseline correction parameters (polynomial degree, ALS lambda)
- **THEN** a red dashed trace shows the preview baseline curve
- **AND** a green solid trace shows the preview corrected spectrum
- **AND** both previews overlay on the current data layer without hiding it

#### Scenario: Preview disappears after baseline run
- **WHEN** a user clicks "Run Baseline Correction"
- **THEN** the red dashed and green preview traces disappear
- **AND** the final baseline-corrected data replaces the previous processed layer
