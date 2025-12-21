# Workflow Orchestration Specification

## ADDED Requirements

### Requirement: Accordion Section Structure

The right panel SHALL organize processing controls into collapsible accordion sections in sequential order.

#### Scenario: Five sequential sections
- **WHEN** the right panel is rendered
- **THEN** five accordion sections appear in order: Processing Range, De-spiking, Baseline Correction, Peak Fitting, Export

#### Scenario: Only one to two sections expanded
- **WHEN** the workflow is in progress
- **THEN** at most one or two accordion sections are expanded at any time
- **AND** completed sections can be manually re-opened for editing

### Requirement: Sequential Workflow Access

Processing sections SHALL enforce sequential dependencies while allowing editing of completed steps.

#### Scenario: Initial access to all sections except fit
- **WHEN** a file is first loaded
- **THEN** Processing Range, De-spiking, and Baseline sections are accessible (can be expanded)
- **AND** Peak Fitting section is disabled with note "Complete baseline correction first"
- **AND** Export section is always accessible

#### Scenario: Peak fitting enabled after baseline
- **WHEN** baseline correction has been run successfully at least once
- **THEN** the Peak Fitting section becomes enabled and expandable

#### Scenario: Re-opening earlier section allowed
- **WHEN** a user has completed baseline and fit steps
- **THEN** the user can re-open and edit the De-spiking or Baseline sections
- **AND** editing triggers stale fit detection (see Stale Fit Detection requirement)

### Requirement: Section Completion and Auto-Expand

Accordion sections SHALL automatically expand the next section upon successful completion of a processing step.

#### Scenario: Successful run expands next section
- **WHEN** a user clicks "Run Despike" and the operation succeeds
- **THEN** the Despike section's status badge updates to "Done"
- **AND** the Baseline Correction section automatically expands
- **AND** the viewport does not auto-scroll (user maintains current position)

#### Scenario: Failed run does not expand next
- **WHEN** a user clicks "Run Baseline Correction" and the operation fails (e.g., invalid parameters)
- **THEN** the Baseline section remains expanded
- **AND** the Peak Fitting section does not expand
- **AND** an inline error message appears in the Baseline section

#### Scenario: Success banner display
- **WHEN** a processing step completes successfully
- **THEN** a brief success message appears within the completed section (e.g., "Despike completed successfully")
- **AND** the success banner auto-dismisses after 3 seconds

### Requirement: Inline Error Handling

Processing errors SHALL be displayed inline within the relevant accordion section with clear guidance.

#### Scenario: Inline error display
- **WHEN** a baseline correction fails due to invalid lambda parameter
- **THEN** a red error box appears at the top of the Baseline Correction section
- **AND** the error message includes specific guidance (e.g., "Lambda must be between 1e2 and 1e9")

#### Scenario: Error badge indicator
- **WHEN** a processing error occurs
- **THEN** a warning icon appears on the corresponding status badge in the left panel file card
- **AND** clicking the badge navigates to the section showing the error details

#### Scenario: Global critical error alert
- **WHEN** a critical file-level error occurs (file load failure, project load error)
- **THEN** a global alert bar appears at the top of the page
- **AND** the alert persists until the user dismisses it or resolves the error

### Requirement: Reset Behavior and Invalidation

The "Reset to Raw" action SHALL clear preprocessing results and invalidate dependent downstream steps.

#### Scenario: Reset clears preprocessing
- **WHEN** a user clicks "Reset to Raw" in the Processing Range section
- **THEN** De-spiked and Baseline-corrected data are cleared for that file
- **AND** Despike and Baseline status badges return to "Not run" state

#### Scenario: Reset invalidates fit
- **WHEN** a user resets preprocessing after a fit has been completed
- **THEN** the existing peak fit is marked as invalid
- **AND** the Fit badge changes to "Not run" state
- **AND** a message appears in the Peak Fitting section: "Preprocessing changed; previous fit cleared. Please run fitting again."

#### Scenario: Plot updates to raw after reset
- **WHEN** a user clicks "Reset to Raw"
- **THEN** the unified plot displays only the raw data layer
- **AND** all other layers (de-spiked, corrected, fit) are hidden

### Requirement: Stale Fit Detection

The application SHALL detect when preprocessing changes invalidate an existing peak fit and mark it as stale.

#### Scenario: Preprocessing change after fit
- **WHEN** a user modifies despike or baseline parameters after a successful peak fit
- **THEN** the existing fit is marked as "stale"
- **AND** the Fit badge displays a warning state (yellow with warning icon)
- **AND** the badge shows tooltip "Refit needed"

#### Scenario: Stale fit notification in Peak Fit section
- **WHEN** a fit is marked as stale
- **THEN** the Peak Fitting section displays a yellow note: "Preprocessing changed; fit no longer matches current data."
- **AND** the note persists until the user runs peak fitting again

#### Scenario: New fit clears stale status
- **WHEN** a user runs peak fitting after preprocessing changes
- **THEN** the stale flag is cleared
- **AND** the Fit badge returns to "Done" state (green with checkmark)

#### Scenario: Export warning for stale fits
- **WHEN** a user attempts to export files with stale fits
- **THEN** a warning message appears: "Some files require refitting; stale fits may be excluded from export."
- **AND** the export dialog allows the user to proceed or cancel
