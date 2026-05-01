"""
Excel preset parser for workflow automation.

This module parses Excel files with one sheet per material-mode combination,
extracting processing settings and peak templates for automated workflows.
"""

import pandas as pd
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
from ..models.preset import MaterialPreset, PeakTemplate, PresetLibrary


def parse_exclusion_ranges(exclusion_str: str) -> List[Tuple[float, float]]:
    """
    Parse exclusion ranges from string format.

    Parameters
    ----------
    exclusion_str : str
        Format: "min1-max1; min2-max2; ..."
        Example: "1200-1400; 2600-2800"

    Returns
    -------
    list of tuple
        List of (x_min, x_max) tuples

    Raises
    ------
    ValueError
        If format is invalid
    """
    if not exclusion_str or pd.isna(exclusion_str):
        return []

    ranges = []
    for pair in exclusion_str.split(';'):
        pair = pair.strip()
        if not pair:
            continue

        parts = pair.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid exclusion range format: '{pair}'. Expected 'min-max'")

        try:
            x_min = float(parts[0].strip())
            x_max = float(parts[1].strip())
        except ValueError:
            raise ValueError(f"Invalid numbers in exclusion range: '{pair}'")

        if x_min >= x_max:
            raise ValueError(f"Invalid exclusion range: x_min ({x_min}) must be < x_max ({x_max})")

        ranges.append((x_min, x_max))

    return ranges


def parse_sheet_name(sheet_name: str) -> Tuple[str, str]:
    """
    Extract material name and mode from sheet name.

    Sheet naming convention: Material_Mode (e.g., 'Graphene_Raman', 'MoS2_PL')

    Parameters
    ----------
    sheet_name : str
        Excel sheet name

    Returns
    -------
    tuple of (str, str)
        (material_name, mode)

    Raises
    ------
    ValueError
        If sheet name format is invalid

    Examples
    --------
    >>> parse_sheet_name('Graphene_Raman')
    ('Graphene', 'Raman')
    >>> parse_sheet_name('MoS2_Raman')
    ('MoS2', 'Raman')
    >>> parse_sheet_name('Silicon_PL')
    ('Silicon', 'PL')
    """
    parts = sheet_name.split('_')

    if len(parts) < 2:
        raise ValueError(
            f"Sheet name must be in format 'Material_Mode' (e.g., 'Graphene_Raman'), "
            f"got '{sheet_name}'"
        )

    # Last part is mode, everything before is material name
    mode = parts[-1]
    material_name = '_'.join(parts[:-1])

    # Validate mode
    if mode not in ['Raman', 'PL']:
        raise ValueError(
            f"Mode must be 'Raman' or 'PL', got '{mode}' in sheet '{sheet_name}'"
        )

    return material_name, mode


def parse_preset_excel(file_path: str) -> PresetLibrary:
    """
    Parse Excel file with one sheet per material-mode combination.

    Algorithm:
    1. Open Excel file
    2. Get all sheet names
    3. For each sheet:
       a. Parse sheet name to extract material_name and mode
       b. Read Row 1-2: Processing settings (headers + values)
       c. Read Row 4+: Peak templates (headers + data rows)
       d. Build MaterialPreset object
       e. Validate preset
    4. Return PresetLibrary with all valid presets

    Parameters
    ----------
    file_path : str
        Path to .xlsx preset file

    Returns
    -------
    PresetLibrary
        Parsed and validated presets

    Raises
    ------
    FileNotFoundError
        If Excel file doesn't exist
    ValueError
        If sheet name invalid or schema malformed
    """
    # Check file exists
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Preset file not found: {file_path}")

    # Load Excel file
    try:
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Failed to read Excel file '{file_path}': {e}")

    presets = {}
    errors_by_sheet = {}

    for sheet_name in xl_file.sheet_names:
        # Skip special sheets (conventionally start with underscore)
        if sheet_name.startswith('_'):
            continue

        try:
            # Parse sheet name
            material_name, mode = parse_sheet_name(sheet_name)

            # Read sheet (no header, read as raw data)
            df = pd.read_excel(xl_file, sheet_name=sheet_name, header=None)

            # Validate minimum rows
            if len(df) < 5:
                raise ValueError(
                    f"Sheet must have at least 5 rows (settings header, settings data, "
                    f"blank, peak header, peak data), got {len(df)} rows"
                )

            # Parse processing settings (Row 0 = headers, Row 1 = values)
            settings_headers = df.iloc[0].tolist()
            settings_values = df.iloc[1].tolist()

            # Create settings dictionary (handle NaN values)
            settings_dict = {}
            for header, value in zip(settings_headers, settings_values):
                if pd.notna(header):  # Skip columns with NaN headers
                    settings_dict[str(header).strip()] = value

            # Validate required settings columns
            required_settings = [
                'x_range_enabled', 'despike_threshold', 'baseline_algorithm'
            ]
            missing_settings = [col for col in required_settings if col not in settings_dict]
            if missing_settings:
                raise ValueError(
                    f"Missing required settings columns: {missing_settings}. "
                    f"Found columns: {list(settings_dict.keys())}"
                )

            # Parse peak templates (Row 3 = headers, Row 4+ = data)
            if len(df) < 5:
                raise ValueError("Sheet must have peak template data (Row 4+)")

            peak_headers = df.iloc[3].tolist()
            peak_headers_clean = [str(h).strip() if pd.notna(h) else None for h in peak_headers]

            # Validate required peak columns
            # Note: 'amplitude' is intentionally NOT required. The fitter
            # auto-estimates amplitude from data and derives bounds from y_max,
            # so the preset value is unused. Tolerated if present (see below).
            required_peak_cols = [
                'peak_label', 'center', 'center_tolerance',
                'width_fwhm', 'shape', 'color'
            ]
            missing_peak_cols = [col for col in required_peak_cols if col not in peak_headers_clean]
            if missing_peak_cols:
                raise ValueError(
                    f"Missing required peak columns: {missing_peak_cols}. "
                    f"Found columns: {[h for h in peak_headers_clean if h]}"
                )

            # Read peak data (Row 4 onwards)
            peak_data = df.iloc[4:].copy()
            peak_data.columns = peak_headers_clean

            # Build PeakTemplates
            peak_templates = []
            for idx, row in peak_data.iterrows():
                # Skip empty rows (no peak_label)
                if pd.isna(row.get('peak_label')) or str(row.get('peak_label')).strip() == '':
                    continue

                try:
                    # Amplitude is optional: column may be missing entirely,
                    # or present with a blank cell. Use 1.0 as a placeholder —
                    # the fitter ignores it and derives bounds from y_max.
                    amp_raw = row.get('amplitude') if 'amplitude' in peak_headers_clean else None
                    amplitude = float(amp_raw) if pd.notna(amp_raw) else 1.0

                    template = PeakTemplate(
                        peak_label=str(row['peak_label']).strip(),
                        center=float(row['center']),
                        center_tolerance=float(row['center_tolerance']),
                        amplitude=amplitude,
                        width_fwhm=float(row['width_fwhm']),
                        shape=float(row['shape']),
                        color=str(row['color']).strip()
                    )
                    peak_templates.append(template)
                except (ValueError, TypeError, KeyError) as e:
                    raise ValueError(
                        f"Invalid peak data at row {idx + 5} (Excel row {idx + 5}): {e}"
                    )

            if len(peak_templates) == 0:
                raise ValueError("No peak templates found (all rows empty or invalid)")

            # Parse exclusion_ranges (optional)
            exclusion_ranges = settings_dict.get('exclusion_ranges', '')
            if pd.isna(exclusion_ranges) or str(exclusion_ranges).strip() == '':
                exclusion_ranges = None
            else:
                exclusion_ranges = str(exclusion_ranges).strip()

            # Build MaterialPreset
            preset = MaterialPreset(
                material_name=material_name,
                mode=mode,
                enabled=True,  # All sheets are considered enabled
                x_range_enabled=bool(settings_dict.get('x_range_enabled', False)),
                x_min=(
                    float(settings_dict['x_min'])
                    if pd.notna(settings_dict.get('x_min')) else None
                ),
                x_max=(
                    float(settings_dict['x_max'])
                    if pd.notna(settings_dict.get('x_max')) else None
                ),
                despike_threshold=float(settings_dict['despike_threshold']),
                baseline_algorithm=str(settings_dict['baseline_algorithm']).strip(),
                baseline_degree=(
                    int(settings_dict['baseline_degree'])
                    if pd.notna(settings_dict.get('baseline_degree')) else None
                ),
                baseline_lambda=(
                    float(settings_dict['baseline_lambda'])
                    if pd.notna(settings_dict.get('baseline_lambda')) else None
                ),
                baseline_p=(
                    float(settings_dict['baseline_p'])
                    if pd.notna(settings_dict.get('baseline_p')) else None
                ),
                exclusion_ranges=exclusion_ranges,
                peak_templates=peak_templates,
                description=str(settings_dict.get('description', '')).strip()
            )

            # Validate preset
            validation_errors = preset.validate()
            if validation_errors:
                errors_by_sheet[sheet_name] = validation_errors
                continue  # Skip invalid preset but continue parsing others

            # Add to presets dictionary
            presets[(material_name, mode)] = preset

        except Exception as e:
            # Collect error but continue parsing other sheets
            errors_by_sheet[sheet_name] = [str(e)]
            continue

    # If all sheets failed, raise error
    if len(presets) == 0 and len(errors_by_sheet) > 0:
        error_msg = "Failed to load any presets. Errors by sheet:\n"
        for sheet, errors in errors_by_sheet.items():
            error_msg += f"\n[{sheet}]:\n"
            for error in errors:
                error_msg += f"  - {error}\n"
        raise ValueError(error_msg)

    # Warn about failed sheets but return successfully parsed presets
    if len(errors_by_sheet) > 0:
        print(f"Warning: {len(errors_by_sheet)} sheet(s) failed to load:")
        for sheet, errors in errors_by_sheet.items():
            print(f"  [{sheet}]: {'; '.join(errors)}")

    return PresetLibrary(
        presets=presets,
        file_path=file_path,
        last_loaded=datetime.now()
    )


def validate_preset_schema(file_path: str) -> List[str]:
    """
    Validate Excel schema without fully loading presets.

    Quick validation checks:
    - File exists and is readable
    - All sheets have valid Material_Mode naming
    - Sheets have minimum required rows
    - Row 1 has required processing settings headers
    - Row 4 has required peak template headers

    Parameters
    ----------
    file_path : str
        Path to .xlsx preset file

    Returns
    -------
    list of str
        Error messages (empty list if valid)
    """
    errors = []

    # Check file exists
    path = Path(file_path)
    if not path.exists():
        errors.append(f"File not found: {file_path}")
        return errors

    # Try to open Excel file
    try:
        xl_file = pd.ExcelFile(file_path, engine='openpyxl')
    except Exception as e:
        errors.append(f"Failed to read Excel file: {e}")
        return errors

    # Validate each sheet
    for sheet_name in xl_file.sheet_names:
        if sheet_name.startswith('_'):
            continue

        # Validate sheet name
        try:
            parse_sheet_name(sheet_name)
        except ValueError as e:
            errors.append(f"[{sheet_name}] {e}")
            continue

        # Read sheet
        try:
            df = pd.read_excel(xl_file, sheet_name=sheet_name, header=None)
        except Exception as e:
            errors.append(f"[{sheet_name}] Failed to read sheet: {e}")
            continue

        # Validate row count
        if len(df) < 5:
            errors.append(
                f"[{sheet_name}] Sheet must have at least 5 rows, got {len(df)}"
            )
            continue

        # Validate settings headers (Row 0)
        settings_headers = df.iloc[0].tolist()
        settings_headers_clean = [str(h).strip() for h in settings_headers if pd.notna(h)]

        required_settings = ['x_range_enabled', 'despike_threshold', 'baseline_algorithm']
        missing_settings = [col for col in required_settings if col not in settings_headers_clean]
        if missing_settings:
            errors.append(
                f"[{sheet_name}] Missing settings columns: {missing_settings}"
            )

        # Validate peak headers (Row 3)
        peak_headers = df.iloc[3].tolist()
        peak_headers_clean = [str(h).strip() for h in peak_headers if pd.notna(h)]

        # 'amplitude' intentionally omitted — see parse_preset_excel().
        required_peaks = [
            'peak_label', 'center', 'center_tolerance',
            'width_fwhm', 'shape', 'color'
        ]
        missing_peaks = [col for col in required_peaks if col not in peak_headers_clean]
        if missing_peaks:
            errors.append(
                f"[{sheet_name}] Missing peak columns: {missing_peaks}"
            )

    return errors
