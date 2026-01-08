"""
Data models for workflow preset system.

This module provides dataclasses for material-specific processing presets
that enable automated workflow execution.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Literal
from datetime import datetime
from .peak import PeakDefinition
from .spectrum import ProcessingSettings


@dataclass
class PeakTemplate:
    """
    Peak template with center tolerance for flexible fitting.

    This is used in presets to define initial peak guesses with
    flexible center position bounds (center ± tolerance).
    """
    peak_label: str
    center: float
    center_tolerance: float  # ± tolerance for center bounds
    amplitude: float
    width_fwhm: float
    shape: float  # Voigt mixing: 0=Gaussian, 1=Lorentzian
    color: str  # Hex color for plotting

    def to_peak_definition(
        self,
        mode: str,
        x_range: Tuple[float, float],
        y_max: float,
        spectral_resolution: float
    ) -> PeakDefinition:
        """
        Convert template to PeakDefinition with auto-calculated bounds.

        The center bounds are overridden with: center ± center_tolerance

        Parameters
        ----------
        mode : str
            "Raman" or "PL" (affects default bounds calculation)
        x_range : tuple
            (x_min, x_max) of spectrum
        y_max : float
            Maximum Y value of spectrum
        spectral_resolution : float
            Median spacing between X points

        Returns
        -------
        PeakDefinition
            Configured peak definition ready for fitting
        """
        peak = PeakDefinition(
            center=self.center,
            amplitude=self.amplitude,
            width_fwhm=self.width_fwhm,
            label=self.peak_label,
            shape=self.shape,
            color=self.color
        )

        # Calculate auto-bounds using existing logic
        peak.calculate_auto_bounds(mode, x_range, y_max, spectral_resolution)

        # Override center bounds with template tolerance
        peak.center_min = max(x_range[0], self.center - self.center_tolerance)
        peak.center_max = min(x_range[1], self.center + self.center_tolerance)

        return peak


@dataclass
class MaterialPreset:
    """
    Complete workflow preset for a specific material and mode.

    Includes processing parameters (despike, baseline) and peak templates
    for automated workflow execution.
    """
    material_name: str
    mode: Literal["Raman", "PL"]
    enabled: bool

    # X-range settings
    x_range_enabled: bool
    x_min: Optional[float]
    x_max: Optional[float]

    # De-spiking settings
    despike_threshold: float

    # Baseline settings
    baseline_algorithm: str  # "Polynomial", "ALS", "None (Skip)"
    baseline_degree: Optional[int]  # For Polynomial
    baseline_lambda: Optional[float]  # For ALS
    baseline_p: Optional[float]  # For ALS
    exclusion_ranges: Optional[str] = None  # Semicolon-separated ranges (e.g., "1200-1400; 2600-2800")

    # Peak templates
    peak_templates: List[PeakTemplate]

    # Metadata
    description: str = ""

    def validate(self) -> List[str]:
        """
        Validate preset parameters against ProcessingSettings constraints.

        Returns
        -------
        list of str
            Error messages (empty list if valid)
        """
        errors = []

        # Mode validation
        if self.mode not in ["Raman", "PL"]:
            errors.append(f"Invalid mode: {self.mode} (must be 'Raman' or 'PL')")

        # Despike threshold
        if not (3.0 <= self.despike_threshold <= 30.0):
            errors.append(
                f"despike_threshold {self.despike_threshold} out of range [3.0, 30.0]"
            )

        # Baseline algorithm
        valid_algos = ["Polynomial", "ALS", "None (Skip)"]
        if self.baseline_algorithm not in valid_algos:
            errors.append(
                f"Invalid baseline_algorithm: {self.baseline_algorithm} "
                f"(must be one of {valid_algos})"
            )

        # Algorithm-specific validation
        if self.baseline_algorithm == "Polynomial":
            if self.baseline_degree is None or not (1 <= self.baseline_degree <= 10):
                errors.append(
                    f"Polynomial algorithm requires baseline_degree in [1, 10], "
                    f"got {self.baseline_degree}"
                )

        if self.baseline_algorithm == "ALS":
            if self.baseline_lambda is None or not (1000 <= self.baseline_lambda <= 1000000):
                errors.append(
                    f"ALS algorithm requires baseline_lambda in [1e3, 1e6], "
                    f"got {self.baseline_lambda}"
                )
            if self.baseline_p is None or not (0.001 <= self.baseline_p <= 0.1):
                errors.append(
                    f"ALS algorithm requires baseline_p in [0.001, 0.1], "
                    f"got {self.baseline_p}"
                )

        # X-range validation
        if self.x_range_enabled:
            if self.x_min is None or self.x_max is None:
                errors.append("x_range_enabled=True requires both x_min and x_max")
            elif self.x_min >= self.x_max:
                errors.append(f"x_min ({self.x_min}) must be < x_max ({self.x_max})")

        # Peak templates validation
        if len(self.peak_templates) == 0:
            errors.append("At least one peak template required")
        if len(self.peak_templates) > 10:
            errors.append(
                f"Maximum 10 peaks allowed (got {len(self.peak_templates)})"
            )

        # Validate individual peak templates
        for i, template in enumerate(self.peak_templates):
            if template.center_tolerance <= 0:
                errors.append(
                    f"Peak {i+1} ({template.peak_label}): center_tolerance must be > 0"
                )
            if template.amplitude <= 0:
                errors.append(
                    f"Peak {i+1} ({template.peak_label}): amplitude must be > 0"
                )
            if template.width_fwhm <= 0:
                errors.append(
                    f"Peak {i+1} ({template.peak_label}): width_fwhm must be > 0"
                )
            if not (0.0 <= template.shape <= 1.0):
                errors.append(
                    f"Peak {i+1} ({template.peak_label}): shape must be in [0.0, 1.0]"
                )
            # Validate hex color format
            if not (template.color.startswith('#') and len(template.color) == 7):
                errors.append(
                    f"Peak {i+1} ({template.peak_label}): color must be hex format #RRGGBB"
                )

        return errors

    def to_processing_settings(self) -> ProcessingSettings:
        """
        Convert preset to ProcessingSettings object.

        Returns
        -------
        ProcessingSettings
            Settings object with preset parameters
        """
        return ProcessingSettings(
            despike_threshold=self.despike_threshold,
            despike_applied=False,  # Will be set to True after execution
            baseline_algorithm=self.baseline_algorithm,
            baseline_degree=self.baseline_degree if self.baseline_degree else 3,
            baseline_lambda=self.baseline_lambda if self.baseline_lambda else 10000.0,
            baseline_p=self.baseline_p if self.baseline_p else 0.001,
            baseline_applied=False,  # Will be set to True after execution
            y_shift=0.0  # Will be calculated during baseline correction
        )


@dataclass
class PresetLibrary:
    """
    Collection of all loaded presets from Excel file.

    Presets are indexed by (material_name, mode) tuple for fast lookup.
    """
    presets: Dict[Tuple[str, str], MaterialPreset]  # Key: (material_name, mode)
    file_path: str
    last_loaded: datetime

    def get_preset(self, sheet_name: str) -> Optional[MaterialPreset]:
        """
        Get preset by full sheet name.

        Parameters
        ----------
        sheet_name : str
            Full sheet name (e.g., "WSe2_Raman", "Graphene_PL")

        Returns
        -------
        MaterialPreset or None
            Preset if found, None otherwise

        Raises
        ------
        ValueError
            If sheet name format is invalid
        """
        from ..io.preset_parser import parse_sheet_name

        try:
            material_name, mode = parse_sheet_name(sheet_name)
            return self.presets.get((material_name, mode))
        except ValueError:
            # If parsing fails, try direct lookup (backwards compatibility)
            return None

    def list_materials(self, mode: Optional[str] = None) -> List[str]:
        """
        List all available material sheet names (optionally filtered by mode).

        Parameters
        ----------
        mode : str, optional
            Filter by "Raman" or "PL". If None, return all materials.

        Returns
        -------
        list of str
            Sorted list of full sheet names (e.g., "WSe2_Raman", "Graphene_PL")
        """
        sheet_names = []
        for (mat, mod), preset in self.presets.items():
            if preset.enabled and (mode is None or mod == mode):
                # Reconstruct full sheet name: Material_Mode
                sheet_name = f"{mat}_{mod}"
                sheet_names.append(sheet_name)
        return sorted(sheet_names)

    def get_sheet_count(self) -> int:
        """Get total number of loaded presets."""
        return len(self.presets)
