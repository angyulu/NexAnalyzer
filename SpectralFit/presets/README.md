# SpectralFit Material Presets

This folder contains the **material_presets.xlsx** file for automated workflow execution.

## Overview

Material presets allow you to:
- Define processing parameters once for each material
- Execute entire workflow (Despike → Baseline → Fitting) with one click
- Share standardized analysis workflows with collaborators
- Add new materials without modifying code

## Excel File Structure

### File: `material_presets.xlsx`

**One sheet per material-mode combination**

Sheet naming: `MaterialName_Mode` (e.g., `Graphene_Raman`, `MoS2_PL`)

### Sheet Layout

```
Row 1: Processing Settings Headers
Row 2: Processing Settings Values
Row 3: (Blank separator)
Row 4: Peak Template Headers
Row 5+: Peak Template Data (one row per peak)
```

## Schema Reference

### Processing Settings (Row 1-2)

| Column | Type | Required | Description | Example Values |
|--------|------|----------|-------------|----------------|
| `x_range_enabled` | boolean | Yes | Enable X-range cropping? | TRUE, FALSE |
| `x_min` | float | Conditional | Min X value (if x_range_enabled=TRUE) | 1200, 500 |
| `x_max` | float | Conditional | Max X value (if x_range_enabled=TRUE) | 2800, 700 |
| `despike_threshold` | float | Yes | Modified Z-score threshold [3-30] | 6.0, 8.0, 10.0 |
| `baseline_algorithm` | string | Yes | Baseline method | "ALS", "Polynomial", "None (Skip)" |
| `baseline_degree` | int | Conditional | Polynomial degree [1-10] (if Polynomial) | 3, 5 |
| `baseline_lambda` | float | Conditional | ALS smoothness [1e3-1e6] (if ALS) | 10000, 50000 |
| `baseline_p` | float | Conditional | ALS asymmetry [0.001-0.1] (if ALS) | 0.001, 0.01 |
| `description` | string | No | User notes | "Graphene on Si/SiO2" |

**Notes:**
- Empty cells (for optional parameters) should be left blank
- Boolean values: TRUE or FALSE (case-insensitive)

### Peak Templates (Row 4+)

| Column | Type | Required | Description | Example Values |
|--------|------|----------|-------------|----------------|
| `peak_label` | string | Yes | Peak name | "D-band", "G-band", "E2g" |
| `center` | float | Yes | Peak center position | 1350, 1580, 2700 |
| `center_tolerance` | float | Yes | ± tolerance for center bounds | 20, 10, 50 |
| `amplitude` | float | Yes | Initial amplitude guess | 5000, 8000, 10000 |
| `width_fwhm` | float | Yes | Full-width-half-max | 50, 60, 10 |
| `shape` | float | Yes | Voigt mixing [0=Gaussian, 1=Lorentzian] | 0.5, 0.3, 0.7 |
| `color` | string | Yes | Hex color for plot | #1f77b4, #ff7f0e |

**Notes:**
- At least one peak required (max 10 peaks)
- center_tolerance defines fitting bounds: `center_min = center - tolerance`, `center_max = center + tolerance`
- Empty rows (no peak_label) are skipped

## Example Materials

### Graphene (Raman)

**Sheet name:** `Graphene_Raman`

**Processing Settings:**
```
x_range_enabled = TRUE
x_min = 1200
x_max = 2800
despike_threshold = 6.0
baseline_algorithm = ALS
baseline_lambda = 10000
baseline_p = 0.001
```

**Peaks:**
- D-band: 1350 ± 20 cm⁻¹
- G-band: 1580 ± 10 cm⁻¹
- 2D-band: 2700 ± 50 cm⁻¹

### MoS2 (Raman)

**Sheet name:** `MoS2_Raman`

**Processing Settings:**
```
x_range_enabled = FALSE
despike_threshold = 8.0
baseline_algorithm = ALS
baseline_lambda = 50000
baseline_p = 0.01
```

**Peaks:**
- E2g: 383 ± 5 cm⁻¹
- A1g: 408 ± 5 cm⁻¹

### Silicon (Raman)

**Sheet name:** `Silicon_Raman`

**Processing Settings:**
```
x_range_enabled = FALSE
despike_threshold = 6.0
baseline_algorithm = Polynomial
baseline_degree = 5
```

**Peaks:**
- Si: 520 ± 3 cm⁻¹

## Adding a New Material

### Method 1: Copy Existing Sheet

1. Open `material_presets.xlsx` in Excel
2. Right-click on existing sheet tab (e.g., `Graphene_Raman`)
3. Select "Move or Copy..."
4. Check "Create a copy"
5. Click OK
6. Right-click new sheet → Rename → Enter `NewMaterial_Mode`
7. Edit Row 2 (processing settings) with new values
8. Edit Row 5+ (peak templates) with new peak positions
9. Save file
10. In SpectralFit app: Click "🔄 Reload" button

### Method 2: Create from Scratch

1. Open `material_presets.xlsx` in Excel
2. Right-click sheet tab area → Insert → New Sheet
3. Name it: `NewMaterial_Mode` (e.g., `GaN_Raman`, `InP_PL`)
4. **Row 1:** Copy headers from existing sheet
   ```
   x_range_enabled | x_min | x_max | despike_threshold | ...
   ```
5. **Row 2:** Enter your processing settings
6. **Row 3:** Leave blank
7. **Row 4:** Copy peak headers from existing sheet
   ```
   peak_label | center | center_tolerance | amplitude | ...
   ```
8. **Row 5+:** Enter your peak data (one row per peak)
9. Save file
10. In SpectralFit app: Click "🔄 Reload" button

## Using Presets in SpectralFit

### 1. Load Preset File

In sidebar:
- **Preset File Path:** Enter or browse to `SpectralFit/presets/material_presets.xlsx`
- Click **🔄 Reload** button
- Success message: "Loaded N presets"

### 2. Select Material

- **Select Material:** Dropdown shows materials for current mode
- Example: If file is Raman mode, only Raman presets appear
- Select material (e.g., "Graphene")

### 3. Run Auto-Workflow

- Review preset info (baseline algorithm, peak count)
- Click **🚀 Run Auto-Workflow** button
- Progress spinner appears
- Success: Results displayed, R² shown
- Failure: Error message with stage and suggestion

### 4. Mode Validation

If file mode ≠ preset mode, you'll see:
```
⚠️ Cannot apply Raman preset to PL file!

Reason: Peak positions and bounds are mode-specific.
Solution: Select a PL preset or change file mode.
```

## Validation Rules

### Processing Settings

- `despike_threshold`: Must be in range [3.0, 30.0]
- `baseline_algorithm`: Must be "Polynomial", "ALS", or "None (Skip)"
- If Polynomial: `baseline_degree` required [1-10]
- If ALS: `baseline_lambda` [1000-1000000] and `baseline_p` [0.001-0.1] required
- If X-range enabled: `x_min` < `x_max` required

### Peak Templates

- At least 1 peak required, maximum 10 peaks
- `center_tolerance` > 0
- `amplitude` > 0
- `width_fwhm` > 0
- `shape` in range [0.0, 1.0]
- `color` must match format `#RRGGBB`

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Sheet name must be Material_Mode" | Invalid sheet name | Rename sheet to format: `MaterialName_Raman` or `MaterialName_PL` |
| "Missing required settings columns" | Missing column headers in Row 1 | Add missing columns from schema |
| "Missing required peak columns" | Missing peak headers in Row 4 | Add missing columns from schema |
| "despike_threshold out of range" | Value < 3 or > 30 | Set value between 3.0 and 30.0 |
| "ALS requires baseline_lambda" | Empty cell for ALS parameter | Enter value between 1000 and 1000000 |
| "No peak templates found" | All peak rows empty | Add at least one peak in Row 5+ |

## Tips & Best Practices

### Peak Center Positions

**For Raman spectra:**
- Use literature values as starting point
- Tolerance: ±10-20 cm⁻¹ for sharp peaks, ±30-50 cm⁻¹ for broad peaks
- Example databases: RRUFF, SpetraBase

**For PL spectra:**
- Account for sample-to-sample variation (strain, doping)
- Tolerance: ±5-10 nm for sharp emission, ±20-30 nm for broad emission

### Baseline Algorithm Selection

- **Polynomial**: Best for simple, smooth backgrounds (degree 2-5 typical)
- **ALS**: Better for fluorescence or complex backgrounds
  - Higher λ = smoother baseline (try 10000-50000)
  - Lower p = more asymmetric (try 0.001-0.01)
- **None (Skip)**: Use if data already background-subtracted

### De-spiking Threshold

- **6.0**: Good default for clean spectra
- **8.0-10.0**: For noisier data (fewer false positives)
- **3.0-5.0**: For very clean data with subtle spikes

### Color Palette for Peaks

Standard colors for better visualization:
```
#1f77b4  (blue)
#ff7f0e  (orange)
#2ca02c  (green)
#d62728  (red)
#9467bd  (purple)
#8c564b  (brown)
#e377c2  (pink)
#7f7f7f  (gray)
#bcbd22  (olive)
#17becf  (cyan)
```

## Troubleshooting

### Preset Not Appearing in Dropdown

**Check:**
1. Sheet name follows `Material_Mode` format
2. Mode matches current file (Raman vs PL)
3. No validation errors (check console after reload)

### Auto-Workflow Fails

**Common causes:**
1. **X-range error**: No data in specified range → Adjust x_min/x_max
2. **Baseline error**: Algorithm parameters incorrect → Check lambda/p/degree values
3. **Fitting error**: Poor initial guesses → Adjust peak centers or tolerances

### Excel File Won't Load

**Check:**
1. File path is correct (default: `SpectralFit/presets/material_presets.xlsx`)
2. File is not open in Excel (close it first)
3. File is valid .xlsx format (not .xls or .csv)
4. No special characters in sheet names (use underscore, not spaces)

## Version History

- **v2.3**: Initial preset system release
- Sheet-per-material design
- Auto-discovery from sheet names
- Mode validation

## Support

For issues or questions:
- GitHub Issues: [github.com/angyulu/Spectrum_Analyzer/issues](https://github.com/angyulu/Spectrum_Analyzer/issues)
- See main documentation: `SpectralFit/Summary.md`
