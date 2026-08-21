"""
Data models for workflow preset system.

This module provides dataclasses for material-specific processing presets
that enable automated workflow execution.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal
from .peak import PeakDefinition


def parse_exclusion_ranges(exclusion_str: Optional[str]) -> List[Tuple[float, float]]:
    """
    Parse exclusion ranges from string format.

    Parameters
    ----------
    exclusion_str : str or None
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
    if not exclusion_str:
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
            # Placeholder: PeakDefinition.amplitude is never consulted by the
            # fitter (auto-estimated from data at fit time; see PeakDefinition's
            # own docstring), so PeakTemplate has no amplitude field of its own.
            amplitude=1.0,
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

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "peak_label": self.peak_label,
            "center": self.center,
            "center_tolerance": self.center_tolerance,
            "width_fwhm": self.width_fwhm,
            "shape": self.shape,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PeakTemplate":
        """Deserialize from dictionary."""
        return cls(**data)


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

    # Peak templates
    peak_templates: List[PeakTemplate]

    # Optional fields with defaults
    exclusion_ranges: Optional[str] = None  # Semicolon-separated ranges (e.g., "1200-1400; 2600-2800")
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

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "material_name": self.material_name,
            "mode": self.mode,
            "enabled": self.enabled,
            "x_range_enabled": self.x_range_enabled,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "despike_threshold": self.despike_threshold,
            "baseline_algorithm": self.baseline_algorithm,
            "baseline_degree": self.baseline_degree,
            "baseline_lambda": self.baseline_lambda,
            "baseline_p": self.baseline_p,
            "peak_templates": [t.to_dict() for t in self.peak_templates],
            "exclusion_ranges": self.exclusion_ranges,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MaterialPreset":
        """Deserialize from dictionary."""
        data = dict(data)
        data["peak_templates"] = [
            PeakTemplate.from_dict(t) for t in data.get("peak_templates", [])
        ]
        return cls(**data)
