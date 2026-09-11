"""
Per-block fingerprinting of a material preset, for stale-figure detection.

Same idea as `fit_staleness.compute_preprocessing_hash` -- hash the settings an
artifact was built from, and compare on the next render -- but at preset
granularity rather than spectrum granularity, and **one fingerprint per block**.

The per-block part is the whole point. A material's optical segmentation costs
about thirty seconds and its Raman fit rather more; a page that fingerprints the
preset as a whole throws both away when an operator nudges one peak's colour.
Hashing `raman` and `optical` separately means an edit clears only the figures
that edit could actually have changed.

Hashes are taken over the block's own `to_dict()`, serialized with sorted keys,
so the fingerprint tracks exactly what gets persisted -- no field can drift out
of the fingerprint by being added to the model and forgotten here.
"""

import hashlib
import json
from typing import Optional


def _digest(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def technique_fingerprint(preset, mode: str) -> Optional[str]:
    """Fingerprint of `preset`'s block for `mode`, or None when it has none.

    None is a value, not an absence: a material that loses its Raman block has
    genuinely changed, and comparing None against a previous hash detects that
    the same way any other edit is detected.
    """
    if preset is None:
        return None
    block = preset.block_for(mode)
    return None if block is None else _digest(block.to_dict())


def optical_fingerprint(preset, layer: str) -> Optional[str]:
    """Fingerprint of `preset`'s optical tuning for `layer`.

    Covers the resolved parameters rather than the stored ones, so a layer that
    falls back to the algorithm's defaults fingerprints as those defaults. The
    layer name is folded in: switching 1L to 2L changes the segmentation even
    when both blocks happen to hold identical numbers, because the class labels
    come from it.
    """
    if preset is None:
        return None
    return _digest({"layer": layer, "params": preset.optical_for(layer).to_dict()})
