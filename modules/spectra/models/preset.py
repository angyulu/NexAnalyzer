"""
Data models for workflow preset system.

This module provides dataclasses for material-specific processing presets
that enable automated workflow execution.
"""

from dataclasses import dataclass, field, fields
from typing import Dict, List, Tuple, Optional
from .peak import PeakDefinition

#: Layers an optical block may be keyed by. The stored form, never the words
#: `contrast.layer_word` prints for them.
OPTICAL_LAYERS = ("1L", "2L")


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

        The template's `center_tolerance` is carried onto the PeakDefinition
        rather than baked into its bounds, because `fit_voigt_peaks` re-runs
        `calculate_auto_bounds` and would otherwise overwrite them with the mode
        default.

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
            # Placeholder: PeakDefinition.intensity is never consulted by the
            # fitter (auto-estimated from data at fit time; see PeakDefinition's
            # own docstring), so PeakTemplate has no intensity field of its own.
            intensity=1.0,
            width_fwhm=self.width_fwhm,
            label=self.peak_label,
            shape=self.shape,
            color=self.color,
            center_tolerance=self.center_tolerance,
        )

        # Calculate auto-bounds using existing logic. This reads
        # center_tolerance, so the bounds it writes are the template's.
        peak.calculate_auto_bounds(mode, x_range, y_max, spectral_resolution)

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
class TechniquePreset:
    """Processing settings and peak templates for one technique of a material.

    This is everything the old flat `MaterialPreset` held except the fields
    that identify the material rather than the measurement (`material_name`,
    `enabled`, `description`) and `mode`, which is no longer stored at all: a
    block's technique is the name of the slot it sits in.

    Every field is defaulted, so a block can be created empty and filled in by
    the editor.
    """

    # X-range settings
    x_range_enabled: bool = False
    x_min: Optional[float] = None
    x_max: Optional[float] = None

    # De-spiking settings
    despike_threshold: float = 8.0

    # Baseline settings
    baseline_algorithm: str = "None (Skip)"  # "Polynomial", "ALS", "None (Skip)"
    baseline_degree: Optional[int] = None    # For Polynomial
    baseline_lambda: Optional[float] = None  # For ALS
    baseline_p: Optional[float] = None       # For ALS

    # Peak templates
    peak_templates: List[PeakTemplate] = field(default_factory=list)

    # Semicolon-separated ranges (e.g., "1200-1400; 2600-2800")
    exclusion_ranges: Optional[str] = None

    def validate(self) -> List[str]:
        """
        Error messages for this block alone (empty list if valid).

        The caller prefixes each with the technique name, since a material
        reports all of its blocks' errors together.
        """
        errors = []

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
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TechniquePreset":
        """Deserialize from dictionary."""
        data = dict(data)
        data["peak_templates"] = [
            PeakTemplate.from_dict(t) for t in data.get("peak_templates", [])
        ]
        return _construct(cls, data, what="technique block")


@dataclass
class OpticalParams:
    """
    Optical-contrast tuning for one layer of one material.

    Every field is `None` by default, meaning "use contrast.py's own default".
    That is deliberate: the numbers live in exactly one place, and a material
    with no optical block produces `analyse_frame(**{})`, which is the vendored
    algorithm untouched.

    `mask_margin` and `ff_divisor` are **not** circular-only, despite
    docs/OM_Contrast_Algo.md quoting circular figures for both. Whether a frame
    is circular is decided per image at runtime by `contrast.is_circular`, so a
    preset has no way to address one frame type; an override applies to both,
    and naming it otherwise would promise a precision that cannot exist.

    `ff_divisor` is a **divisor**, not a sigma: the flat-field blur runs at
    max(H, W) / ff_divisor, so a larger number means a *smaller* sigma.
    """

    nsigma: Optional[float] = None
    minpx: Optional[int] = None
    mask_margin: Optional[float] = None
    ff_divisor: Optional[float] = None

    #: Field name -> the `contrast.analyse_frame` keyword it sets.
    _KWARGS = {
        "nsigma": "nsigma",
        "minpx": "minpx",
        "mask_margin": "margin",
        "ff_divisor": "ff_divisor",
    }

    def as_kwargs(self) -> dict:
        """
        Only the fields that are set, keyed as `analyse_frame` wants them.

        An unset field is omitted rather than passed as None, so the defaults
        stay written down once, in contrast.py.
        """
        return {
            keyword: getattr(self, name)
            for name, keyword in self._KWARGS.items()
            if getattr(self, name) is not None
        }

    def validate(self) -> List[str]:
        """Error messages for this block alone (empty list if valid)."""
        errors = []
        if self.nsigma is not None and not (1.0 <= self.nsigma <= 10.0):
            errors.append(f"nsigma {self.nsigma} out of range [1.0, 10.0]")
        if self.minpx is not None and self.minpx < 1:
            errors.append(f"minpx must be >= 1 (got {self.minpx})")
        if self.mask_margin is not None and not (0.0 <= self.mask_margin < 0.5):
            errors.append(f"mask_margin {self.mask_margin} out of range [0.0, 0.5)")
        if self.ff_divisor is not None and not (1.0 <= self.ff_divisor <= 64.0):
            errors.append(f"ff_divisor {self.ff_divisor} out of range [1.0, 64.0]")
        return errors

    def to_dict(self) -> dict:
        """Only the fields that are set; absent means "algorithm default"."""
        return {
            name: getattr(self, name)
            for name in self._KWARGS
            if getattr(self, name) is not None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OpticalParams":
        """Deserialize from dictionary."""
        return _construct(cls, dict(data), what="optical block")


def _construct(cls, data: dict, what: str):
    """
    `cls(**data)`, but naming the offending key when one is unknown.

    A bare ``TypeError: __init__() got an unexpected keyword argument 'mode'``
    says nothing about which entry in materials.json to go and fix, which is
    the only thing the reader needs to know.
    """
    allowed = {f.name for f in fields(cls)}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise TypeError(
            f"Unknown {what} field(s) {unknown}; expected any of {sorted(allowed)}"
        )
    return cls(**data)


@dataclass
class MaterialPreset:
    """
    Everything the app knows about one material.

    Keyed by material name alone. Technique is no longer part of a preset's
    identity -- it comes from the filename, via
    `parser.detect_mode_from_filename` -- so one material holds a `raman`
    block, a `pl` block, or both, and either may be absent.

    `optical` splits a level further, by layer ("1L", "2L"), because optical
    contrast against SiO2/Si genuinely differs between a monolayer and a
    bilayer, while a Raman or PL spectrum does not: the signal says which peaks
    it has. Layers are stored as "1L"/"2L", never as the words
    `contrast.layer_word` prints for them -- that helper is one-way
    presentation and passes unknown values through, so keying persisted JSON by
    its output would orphan every stored block the day the wording changed, and
    would let the file express a "Trilayer" the UI can never select.
    """

    material_name: str
    enabled: bool = True
    description: str = ""

    raman: Optional[TechniquePreset] = None
    pl: Optional[TechniquePreset] = None
    optical: Dict[str, OpticalParams] = field(default_factory=dict)

    #: Technique name -> the attribute holding its block.
    _BLOCKS = {"Raman": "raman", "PL": "pl"}

    def block_for(self, mode: str) -> Optional[TechniquePreset]:
        """The block for `mode` ("Raman"/"PL"), or None if there isn't one."""
        attribute = self._BLOCKS.get(mode)
        return getattr(self, attribute) if attribute else None

    def optical_for(self, layer: str) -> "OpticalParams":
        """
        Tuning for `layer`, or an all-defaults block when that layer is untuned.

        Never None: an untuned layer is a legitimate state that runs the
        algorithm's own defaults, and the page says which it is using rather
        than refusing to run.
        """
        return self.optical.get(layer) or OpticalParams()

    def validate(self) -> List[str]:
        """Error messages across every block (empty list if valid)."""
        errors = []

        if self.raman is None and self.pl is None and not self.optical:
            errors.append(
                f"'{self.material_name}' has no Raman, PL or optical settings; "
                f"a preset with no blocks does nothing"
            )

        for mode, attribute in self._BLOCKS.items():
            block = getattr(self, attribute)
            if block is not None:
                errors.extend(f"{mode}: {e}" for e in block.validate())

        for layer, params in self.optical.items():
            if layer not in OPTICAL_LAYERS:
                # Reported, not dropped. The loader keeps unknown layers so that
                # "I loaded the file" never quietly means "I deleted part of it";
                # flagging it here is what makes the choice visible.
                errors.append(
                    f"Optical: unknown layer '{layer}' (expected one of "
                    f"{list(OPTICAL_LAYERS)}); it is preserved but unused"
                )
            errors.extend(f"Optical {layer}: {e}" for e in params.validate())

        return errors

    def to_dict(self) -> dict:
        """
        Serialize to dictionary for JSON export.

        Absent blocks are **omitted**, not written as null: "this material has
        no PL" and "this material has an empty PL block" are different states,
        and only omission round-trips the first one.
        """
        out: dict = {
            "material_name": self.material_name,
            "enabled": self.enabled,
            "description": self.description,
        }
        if self.raman is not None:
            out["raman"] = self.raman.to_dict()
        if self.pl is not None:
            out["pl"] = self.pl.to_dict()
        if self.optical:
            out["optical"] = {
                layer: params.to_dict() for layer, params in self.optical.items()
            }
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "MaterialPreset":
        """
        Deserialize from dictionary.

        Nested blocks are reconstructed explicitly: `cls(**data)` would hand
        `raman` a raw dict, and every later attribute access would fail
        somewhere far away from the entry that caused it.
        """
        data = dict(data)
        for attribute in cls._BLOCKS.values():
            if data.get(attribute) is not None:
                data[attribute] = TechniquePreset.from_dict(data[attribute])
            else:
                data.pop(attribute, None)
        if data.get("optical") is not None:
            data["optical"] = {
                layer: OpticalParams.from_dict(params)
                for layer, params in data["optical"].items()
            }
        else:
            data.pop("optical", None)
        return _construct(cls, data, what=f"material '{data.get('material_name')}'")
