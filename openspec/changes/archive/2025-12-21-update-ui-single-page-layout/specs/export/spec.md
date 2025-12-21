# Export Specification

## MODIFIED Requirements

### Requirement: Single Export Entry Point

The export functionality SHALL be accessible from a single unified section at the bottom of the right control panel.

#### Scenario: Export section location
- **WHEN** a user scrolls to the bottom of the right panel
- **THEN** an "Export" accordion section is visible as the fifth and final section

#### Scenario: Export button and dialog
- **WHEN** a user expands the Export section
- **THEN** a single "Export…" button is displayed
- **AND** clicking the button opens an export options dialog

### Requirement: Export File Selection Options

The export dialog SHALL provide three file selection modes for export operations.

#### Scenario: Export current file option
- **WHEN** a user opens the export dialog
- **THEN** an option "Export current file" is available
- **AND** selecting this option exports only the currently selected file in the left panel

#### Scenario: Export all processed files option
- **WHEN** a user opens the export dialog
- **THEN** an option "Export all processed files" is available
- **AND** selecting this option exports all files that have completed at least one processing step

#### Scenario: Export only successful fits option
- **WHEN** a user opens the export dialog
- **THEN** an option "Export only files with successful fit" is available
- **AND** selecting this option exports only files where `fit_done == True` and `fit_stale == False`

### Requirement: Stale Fit Export Warning

The export dialog SHALL warn users when attempting to export files with stale fits.

#### Scenario: Stale fit detection in export
- **WHEN** a user selects an export option that includes files with stale fits
- **THEN** a warning message appears: "Some files require refitting; stale fits may be excluded from export."
- **AND** the dialog provides options: "Exclude stale fits and continue" or "Cancel"

#### Scenario: Proceeding with stale fit exclusion
- **WHEN** a user chooses "Exclude stale fits and continue"
- **THEN** the export proceeds with only non-stale files included
- **AND** a summary message displays: "Exported X files (Y files skipped due to stale fits)"

## ADDED Requirements

### Requirement: Export Format Preservation

Export functionality SHALL maintain all v2.1 export formats and metadata without changes.

#### Scenario: Existing formats supported
- **WHEN** a user completes an export operation
- **THEN** the output includes Master CSV, individual file CSVs, and plot images (PNG/HTML) as in v2.1
- **AND** all metadata columns from v2.1 are present (including v2.1 enhancements: mode, X-range, plot width preset)
