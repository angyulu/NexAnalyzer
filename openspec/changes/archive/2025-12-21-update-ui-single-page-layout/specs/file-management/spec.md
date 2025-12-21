# File Management Specification

## ADDED Requirements

### Requirement: File Status Cards

Each loaded file SHALL be displayed as a card in the left panel with mode indicator and processing status badges.

#### Scenario: Card display elements
- **WHEN** a file is loaded into the application
- **THEN** a card appears in the left panel showing the filename
- **AND** the card displays a mode chip indicating "Raman" or "PL"
- **AND** the card displays three status badges: Despike, Baseline, and Fit

#### Scenario: Auto-detected mode display
- **WHEN** a file is loaded and mode is auto-detected from filename patterns (RM*/PL*)
- **THEN** the mode chip displays the detected mode
- **AND** the mode chip is visually distinguishable (e.g., different colors for Raman vs PL)

### Requirement: Status Badge States

Status badges SHALL indicate processing completion state with three visual states: Not run, Done, and Warning.

#### Scenario: Initial badge state
- **WHEN** a file is newly loaded
- **THEN** all three badges (Despike, Baseline, Fit) display "Not run" state with gray styling

#### Scenario: Completed step badge
- **WHEN** a processing step completes successfully with non-default settings
- **THEN** the corresponding badge changes to "Done" state with green styling and checkmark icon

#### Scenario: Warning badge for stale fit
- **WHEN** preprocessing parameters change after a fit has been completed
- **THEN** the Fit badge changes to "Warning" state with yellow styling and warning icon

#### Scenario: Reset clears badge
- **WHEN** a user clicks "Reset to Raw" for a file
- **THEN** the Despike and Baseline badges return to "Not run" state
- **AND** the Fit badge returns to "Not run" state (fit invalidated)

### Requirement: Clickable Badge Navigation

Status badges SHALL be clickable and navigate to the corresponding processing section.

#### Scenario: Badge click expands section
- **WHEN** a user clicks the "Despike" badge
- **THEN** the right panel scrolls to and expands the Despike accordion section

#### Scenario: Badge click on disabled section shows message
- **WHEN** a user clicks the "Fit" badge and baseline has not been run
- **THEN** a tooltip or message displays: "Complete previous steps first"
- **AND** the Fit section does not expand

### Requirement: File Error Indicators

Critical file-level errors SHALL be visually indicated on file cards.

#### Scenario: Parse error indicator
- **WHEN** a file fails to parse (invalid format, missing columns)
- **THEN** the file card displays a red border and "Error" label
- **AND** the card shows a brief error message (e.g., "Parse failed: invalid format")

#### Scenario: Processing error indicator
- **WHEN** a processing step encounters an error for a specific file
- **THEN** a warning icon appears on the corresponding status badge
- **AND** the file card remains selectable for error investigation
