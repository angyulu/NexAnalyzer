"""
Trace styling shared by the on-screen plot and the exported figures.

The Spectra page (`live_plot`) and the Sample Report's figures (`fit_plot`) draw
the same three things — the data, the total fit, and the residuals — and used to
each pick their own colors. They disagreed: on screen the fit was a black dashed
line over blue points, while the .pptx drew it as a solid orange line over
muted-blue points, so a report didn't look like the spectrum it came from. One
definition here, imported by both, is what keeps them the same.

Colors are hex rather than CSS names ("#0000FF", not "blue") because the .pptx
legend parses them with `core.report.pptx._hex_to_rgb`, which falls back to
black for anything it can't read. A CSS name would still plot correctly and
silently render a black swatch beside it. The values are the CSS names the
on-screen plot used before this module existed: blue, black and green.

Only the traces *both* plotters draw belong here. The Spectra page's own layers
— the de-spiked and baseline-corrected series, the live previews — are its
alone, and stay in `live_plot`.
"""

# The measured spectrum: markers, not a line, in both plotters.
DATA_COLOR = "#0000FF"  # CSS "blue"

# The summed fit. Dashed so it stays readable where it sits on top of the data
# it is fitting, which is most of its length.
FIT_TOTAL_COLOR = "#000000"  # CSS "black"
FIT_TOTAL_DASH = "dash"

# Data minus fit. Green, and never the same color as the fit or the data, since
# the whole point of the panel is telling them apart.
RESIDUAL_COLOR = "#008000"  # CSS "green"

# Individual fitted peaks keep their own `FittedPeak.color`; only the style is
# shared. Solid, so the dashed total fit reads as the distinct thing, and
# semi-transparent so overlapping components stay legible.
COMPONENT_DASH = None
COMPONENT_OPACITY = 0.7
