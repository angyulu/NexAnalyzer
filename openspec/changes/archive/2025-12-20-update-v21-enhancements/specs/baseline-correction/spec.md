# Baseline Correction Capability

## MODIFIED Requirements

### Requirement: Spectrum Data Validation

The system SHALL accept spectrum data with negative intensity (Y) values to support background-subtracted spectra and detector offsets.

**Previous Behavior (v2.0):** Y values must be non-negative; negative values cause validation error.

**New Behavior (v2.1):** Y values may be negative; validation accepts full real number range.

#### Scenario: Load spectrum with negative Y values

- **WHEN** user uploads a file with Y values ranging from -50.0 to 800.0
- **THEN** system successfully parses and loads the spectrum
- **AND** no validation error is raised
- **AND** negative values are preserved in `SpectrumData.Y` array

#### Scenario: Display negative Y values in plots

- **WHEN** spectrum contains negative Y values
- **THEN** plots display full Y-axis range including negative region
- **AND** axis labels and hover tooltips show negative values correctly

## ADDED Requirements

### Requirement: Automatic Y-Shift for Baseline Algorithms

The system SHALL automatically apply an internal vertical shift when baseline correction algorithms encounter negative Y values, ensuring algorithmic stability while preserving original scale in results.

**Algorithm:**
1. Detect if `min(Y) < 0`
2. If true, compute `y_shift = abs(min(Y)) + epsilon` (epsilon = small positive buffer, e.g., 1.0)
3. Apply baseline algorithm to `Y_shifted = Y + y_shift`
4. Return baseline-corrected data as `Y_corrected = Y - baseline` (in original scale)

**Transparency:**
- Log shift amount in per-file processing state
- Shift is purely internal; users see original Y scale in corrected output

#### Scenario: Polynomial baseline with negative Y

- **WHEN** spectrum has Y values from -100 to 500
- **AND** user selects polynomial baseline (degree 2)
- **THEN** system computes `y_shift = 100 + 1 = 101`
- **AND** fits polynomial to `Y + 101`
- **AND** subtracts baseline from original Y (not shifted)
- **AND** baseline-corrected Y preserves original scale (may still be negative)

#### Scenario: ALS baseline with negative Y

- **WHEN** spectrum has minimum Y value of -25.3
- **AND** user selects ALS baseline (λ=10⁴, p=0.001)
- **THEN** system applies shift of 26.3 internally
- **AND** runs ALS on shifted data
- **AND** returns corrected Y in original scale
- **AND** logs "Applied automatic Y-shift: 26.3" in processing state

#### Scenario: No shift for all-positive Y

- **WHEN** spectrum has Y values from 10.0 to 1000.0 (all positive)
- **THEN** system detects no negative values
- **AND** no shift is applied (shift amount = 0)
- **AND** baseline algorithms run on original Y directly

### Requirement: Transparency and User Feedback

The system SHALL inform users that negative Y values are handled automatically without requiring manual intervention.

#### Scenario: Tooltip explains automatic handling

- **WHEN** user hovers over baseline algorithm selector
- **THEN** tooltip displays: "Negative Y values are automatically handled via internal shifting"
- **AND** tooltip explains that results remain in original scale

#### Scenario: Status message when shift applied

- **WHEN** baseline correction applies Y-shift (shift > 0)
- **THEN** system briefly displays status message: "Applied automatic Y-shift for baseline stability"
- **AND** message auto-dismisses after 3 seconds

#### Scenario: Project JSON logs shift amount

- **WHEN** user saves project after baseline correction with shift
- **THEN** project JSON includes per-file `y_shift` field with numeric value
- **AND** loading project restores shift metadata (for transparency, not reapplication)

### Requirement: Baseline Correction Robustness

The system SHALL handle edge cases in baseline correction with automatic Y-shift without user-visible errors.

#### Scenario: Large negative offset

- **WHEN** spectrum has constant offset of -5000 (all Y values very negative)
- **AND** user applies polynomial baseline
- **THEN** system successfully computes baseline with shift of 5001
- **AND** corrected Y values are returned in original scale
- **AND** no overflow or numerical instability occurs

#### Scenario: Mixed positive and negative Y after correction

- **WHEN** baseline-corrected spectrum contains both positive and negative Y
- **THEN** system displays corrected spectrum with full range
- **AND** subsequent fitting algorithms handle negative-corrected Y gracefully (or user re-shifts manually if needed)

### Requirement: Real-time Baseline Preview

The system SHALL provide instant visual feedback of baseline correction results as users adjust parameters, enabling iterative parameter tuning without applying changes to processed data.

**User Workflow:**
1. User adjusts baseline parameters (algorithm, degree, λ, p)
2. Preview plot updates instantly showing both baseline curve and corrected spectrum
3. User iterates until satisfied with visual result
4. User clicks "Run Baseline Correction" to apply changes

**Visual Design:**
- Raw data: Blue markers (existing)
- Currently applied processed data: Orange line (existing)
- Preview baseline curve: Red dashed line (NEW)
- Preview corrected spectrum: Green semi-transparent line (NEW)

**Performance:**
- Polynomial preview: Instant (<100ms)
- ALS preview: May show spinner for large spectra (>5000 points)
- Caching prevents redundant calculations on identical parameters

#### Scenario: Adjust polynomial degree and see instant preview

- **WHEN** user loads a spectrum and navigates to Pre-process tab
- **AND** user moves the "Polynomial Degree" slider from 2 to 3
- **THEN** preview plot updates within 100ms
- **AND** plot shows red dashed baseline curve fitted with degree 3
- **AND** plot shows green semi-transparent corrected spectrum
- **AND** orange "Processed" line remains unchanged (previous state)
- **AND** `spectrum.processed_data` is NOT modified (non-destructive preview)

#### Scenario: Switch between Polynomial and ALS algorithms

- **WHEN** user has polynomial degree 3 preview displayed
- **AND** user selects "ALS" radio button
- **THEN** preview plot updates showing ALS baseline with default parameters (λ=100000, p=0.001)
- **AND** red dashed line shows ALS-fitted baseline
- **AND** green line shows ALS-corrected spectrum
- **AND** spinner may appear briefly if computation takes >500ms

#### Scenario: Apply baseline correction from cached preview

- **WHEN** user has adjusted polynomial degree to 5 (preview visible)
- **AND** user clicks "Run Baseline Correction" button
- **THEN** system applies baseline correction within 50ms (no recomputation)
- **AND** orange "Processed" line updates to match green preview
- **AND** red/green preview traces disappear
- **AND** success message displays: "✅ Baseline corrected using Polynomial"
- **AND** `spectrum.processed_data.Y` now contains corrected data

#### Scenario: Preview cache invalidation on parameter change

- **WHEN** user has polynomial degree 3 preview cached
- **AND** user changes degree slider to 4
- **THEN** system detects cache key mismatch (cache_key changes from "filename_Polynomial_3" to "filename_Polynomial_4")
- **AND** system recomputes baseline with degree 4
- **AND** preview plot updates with new baseline curve
- **AND** new result is cached with updated cache key

#### Scenario: Reset to Raw clears preview

- **WHEN** user has baseline preview visible
- **AND** user clicks "Reset to Raw" button
- **THEN** `spectrum.processed_data` reverts to raw data
- **AND** preview cache is cleared from session state
- **AND** red/green preview traces disappear
- **AND** plot shows only blue markers (raw) and orange line (reset processed)

#### Scenario: Switch files maintains independent preview state

- **WHEN** user has file "sample1.txt" with polynomial degree 3 preview
- **AND** user switches to file "sample2.txt" in sidebar
- **THEN** preview cache for sample1 is preserved (cache key includes filename)
- **AND** sample2 shows no preview initially (independent state)
- **AND** user can adjust parameters for sample2 without affecting sample1's cached preview

### Technical Implementation Notes

**Session State Structure:**
```python
st.session_state['baseline_preview'] = {
    'cache_key': str,           # e.g., "sample.txt_Polynomial_3"
    'baseline_curve': np.ndarray,  # Fitted baseline in original Y scale
    'y_corrected': np.ndarray,     # Baseline-corrected Y in original scale
    'shift': float,                # Auto-shift amount (for transparency)
    'algorithm': str,              # 'Polynomial' or 'ALS'
    'params': dict                 # {'degree': 3} or {'lambda': 1e4, 'p': 0.001}
}
```

**Cache Key Generation:**
- Polynomial: `f"{filename}_Polynomial_{degree}"`
- ALS: `f"{filename}_ALS_{lambda_val}_{p_val}"`

**Integration with Existing Features:**
- X-range indicators: Preview respects X-range selection (computes on filtered data)
- Plot width control: Preview traces use global width preset
- Auto Y-shift: Preview displays baseline/corrected in original scale (shift handled internally)
- Despike state: Preview computes on current `processed_data.Y` (respects prior despike)
