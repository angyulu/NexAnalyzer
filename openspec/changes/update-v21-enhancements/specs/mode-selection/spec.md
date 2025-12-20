# Mode Selection Capability

## ADDED Requirements

### Requirement: Automatic Mode Detection from Filename

The system SHALL automatically detect the spectroscopy mode (Raman or PL) based on filename prefixes when files are uploaded.

**Detection Rules:**
- Filenames starting with `RM` (case-insensitive) → Auto-set to Raman mode
- Filenames starting with `PL` (case-insensitive) → Auto-set to PL mode
- Other patterns → No automatic mode change

**Behavior:**
- Auto-detection occurs only on initial file load
- Manual mode toggle always overrides auto-detection
- Auto-detected mode is saved in per-file state and project JSON with `auto_detected: true` flag

#### Scenario: Detect Raman mode from RM prefix

- **WHEN** user uploads a file named `RM_carbon_sample.txt`
- **THEN** system automatically sets mode to "Raman" for that file
- **AND** displays dismissible banner: "Mode auto-detected as Raman from filename; change manually if incorrect"
- **AND** saves `auto_detected: true` in file state

#### Scenario: Detect PL mode from PL prefix (case-insensitive)

- **WHEN** user uploads a file named `pl_emission_test.txt`
- **THEN** system automatically sets mode to "PL" for that file
- **AND** displays dismissible banner with 5-second auto-dismiss
- **AND** applies PL-specific units (nm) and fitting bounds (±30 nm)

#### Scenario: No auto-detection for non-matching filename

- **WHEN** user uploads a file named `sample_001.txt`
- **THEN** system keeps current mode setting unchanged
- **AND** no banner is displayed
- **AND** saves `auto_detected: false` in file state

#### Scenario: Manual override of auto-detected mode

- **WHEN** system auto-detects mode as "Raman" from filename `RM_test.txt`
- **AND** user manually toggles mode to "PL"
- **THEN** system respects manual selection
- **AND** `auto_detected` flag remains true (records original detection occurred)
- **AND** current mode is "PL"

### Requirement: Dismissible Auto-Detection Banner

The system SHALL display a temporary notification when auto-detection triggers to inform users of the automatic mode change.

#### Scenario: Banner auto-dismisses after timeout

- **WHEN** auto-detection banner is displayed
- **THEN** banner automatically disappears after 5 seconds
- **OR** user clicks dismiss button

#### Scenario: Banner content includes instructions

- **WHEN** banner is displayed for Raman auto-detection
- **THEN** banner text reads: "Mode auto-detected as Raman from filename; change manually if incorrect"
- **AND** banner is styled as informational (not warning or error)

### Requirement: Per-File Mode State Persistence

The system SHALL save the auto-detection flag and selected mode for each file independently in session state and project JSON.

#### Scenario: Project JSON includes auto-detection metadata

- **WHEN** user saves project with 2 files (one auto-detected, one manual)
- **THEN** JSON contains per-file entries with `mode` and `auto_detected` fields
- **AND** reloading project restores both mode and auto-detection status

#### Scenario: Export CSV includes auto-detection column

- **WHEN** user exports Master CSV
- **THEN** CSV includes `auto_detected` column (TRUE/FALSE)
- **AND** row for `RM_sample.txt` shows `auto_detected: TRUE`
- **AND** row for `manual_spectrum.txt` shows `auto_detected: FALSE`
