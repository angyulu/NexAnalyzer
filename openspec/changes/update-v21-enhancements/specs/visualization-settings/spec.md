# Visualization Settings Capability

## ADDED Requirements

### Requirement: Adjustable Plot Width

The system SHALL provide user-configurable plot width controls with preset options to accommodate different display sizes and inspection needs.

**Preset Options:**
- **Compact:** 60% of content area width
- **Standard:** 75% of content area width (default)
- **Wide:** 90% of content area width
- **Full:** 100% of content area width

**Behavior:**
- Width setting applies globally to all plots across all tabs (Pre-process, Fit Model, Visualize & Export)
- Setting is session-level (same for all files in current session)
- Setting persists in session state and project JSON
- Plotly interactivity (zoom, pan, hover) preserved at all widths

#### Scenario: Change plot width to Compact

- **WHEN** user selects "Compact" from plot width control
- **THEN** all plots resize to 60% of content area width
- **AND** resize applies immediately to currently visible plot
- **AND** resize persists when switching tabs or files

#### Scenario: Default width is Standard

- **WHEN** user opens SpectralFit for first time (no saved project)
- **THEN** plot width is set to "Standard" (75%)
- **AND** all plots render at 75% width

#### Scenario: Width setting saved in project JSON

- **WHEN** user sets plot width to "Wide" and saves project
- **THEN** project JSON includes `plot_width_preset: "Wide"` field
- **AND** reloading project restores "Wide" setting
- **AND** all plots render at 90% width immediately after load

#### Scenario: Full width maximizes plot area

- **WHEN** user selects "Full" plot width
- **THEN** plots expand to 100% of content area
- **AND** no horizontal scrolling occurs
- **AND** Plotly toolbar and legend remain accessible

#### Scenario: Plotly interactivity preserved

- **WHEN** plot width is set to any preset (Compact, Standard, Wide, Full)
- **THEN** zoom, pan, and hover functionality work correctly
- **AND** legend checkboxes toggle component visibility
- **AND** plot responsiveness is maintained (no lag)

### Requirement: Plot Width Control UI

The system SHALL provide an intuitive control widget for selecting plot width presets, accessible from the sidebar or main plot area.

#### Scenario: Control widget in sidebar

- **WHEN** user views sidebar
- **THEN** plot width control is visible as radio buttons or selectbox
- **AND** current selection is highlighted
- **AND** help text explains preset percentages

#### Scenario: Width change applies to all plots

- **WHEN** user is viewing Pre-process tab with raw data plot
- **AND** changes width to "Compact"
- **THEN** raw data plot resizes to 60% immediately
- **AND** switching to Fit Model tab shows fit plot also at 60%
- **AND** switching to Visualize & Export shows composite plot at 60%

### Requirement: Session-Level Width Persistence

The system SHALL maintain plot width setting across file switches within a session, but allow per-project customization when loading saved projects.

#### Scenario: Width persists across file switches

- **WHEN** user sets plot width to "Wide"
- **AND** switches from file A to file B using file selector
- **THEN** plot width remains "Wide" for file B
- **AND** all plots for file B render at 90% width

#### Scenario: Loading project overrides session width

- **WHEN** current session has plot width set to "Compact"
- **AND** user loads project JSON with `plot_width_preset: "Full"`
- **THEN** plot width changes to "Full" for loaded project
- **AND** all plots render at 100% width

#### Scenario: No width setting in v2.0 project

- **WHEN** user loads a v2.0 project JSON (missing `plot_width_preset` field)
- **THEN** system defaults to "Standard" (75% width)
- **AND** no error or warning is displayed
- **AND** plots render correctly at default width
