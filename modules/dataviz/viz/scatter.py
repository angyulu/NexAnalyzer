"""
A config dict and a DataFrame in, a Plotly scatter out.

Pure: no Streamlit, no file access. The page collects the settings, this turns
them into a figure, and that separation is what lets the interesting part —
which combinations are legal, and which quietly produce a useless chart — be
unit tested.

Two kinds of bad input are handled differently on purpose.

A **crash** is prevented. ``size`` given a text column, or one holding negative
numbers, raises out of Plotly with a message that names neither the column nor
the control; `build_scatter` checks first and raises one that does. Likewise
``trendline`` without statsmodels installed, which fails on import deep inside
px with nothing to suggest the fix.

A **bad-looking chart** is not prevented, only reported. `cardinality_warnings`
flags a facet over 30 distinct values or a discrete colour over 20 — thresholds
past which the output is unreadable rather than wrong. The page shows them and
plots anyway, because 40 facets is occasionally exactly what someone wants and
the person choosing knows their data better than a threshold does.
"""

from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

#: Distinct values past which a facet column produces one subplot per value in
#: numbers that hang the browser rather than inform.
FACET_WARN_LIMIT = 30

#: Distinct values past which a discrete colour legend is taller than the plot.
COLOR_WARN_LIMIT = 20

#: Marginal-plot choices; "" means none.
MARGINAL_CHOICES = ("", "rug", "box", "violin", "histogram")

#: Trendline choices; "" means none. Deliberately only the two that work with
#: library defaults -- "rolling", "expanding" and "ewm" all require a
#: ``trendline_options`` window that this panel doesn't expose, and offering a
#: control that raises when used is worse than not offering it.
TRENDLINE_CHOICES = ("", "ols", "lowess")

#: Plotly figure templates.
TEMPLATE_CHOICES = (
    "plotly", "plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white", "presentation",
)

#: Every key `build_scatter` understands, with its inert default. A config is a
#: plain dict so it round-trips through JSON without a schema migration story.
DEFAULT_CONFIG: Dict = {
    "x": None,
    "y": None,
    "color": None,
    "symbol": None,
    "size": None,
    "size_max": 20,
    "opacity": 0.8,
    "hover_name": None,
    "hover_data": [],
    "facet_row": None,
    "facet_col": None,
    "facet_col_wrap": 0,
    "error_x": None,
    "error_y": None,
    "marginal_x": "",
    "marginal_y": "",
    "trendline": "",
    "log_x": False,
    "log_y": False,
    "range_x_min": None,
    "range_x_max": None,
    "range_y_min": None,
    "range_y_max": None,
    "template": "plotly_white",
    "title": "",
}


def numeric_columns(df: pd.DataFrame) -> List[str]:
    """Columns Plotly can use where a number is required.

    This is what the ``size`` dropdown offers. Everything else offers every
    column, because a text column on an axis or in a colour is a legitimate
    (if sometimes unhelpful) choice, whereas a text column in ``size`` is an
    exception.
    """
    return [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def statsmodels_available() -> bool:
    """Whether ``trendline`` can be used at all."""
    try:
        import statsmodels.api  # noqa: F401

        return True
    except Exception:
        return False


def cardinality_warnings(df: pd.DataFrame, config: Dict) -> List[str]:
    """Human-readable warnings about choices that will render badly.

    Returned rather than raised: every one of these still produces a figure.
    """
    warnings: List[str] = []

    for key in ("facet_row", "facet_col"):
        column = config.get(key)
        if column and column in df.columns:
            distinct = int(df[column].nunique(dropna=True))
            if distinct > FACET_WARN_LIMIT:
                warnings.append(
                    "{} = '{}' has {} distinct values, so the plot becomes {} subplots. "
                    "This will be slow and hard to read.".format(key, column, distinct, distinct)
                )

    color = config.get("color")
    if color and color in df.columns and not pd.api.types.is_numeric_dtype(df[color]):
        distinct = int(df[color].nunique(dropna=True))
        if distinct > COLOR_WARN_LIMIT:
            warnings.append(
                "color = '{}' has {} distinct values, so the legend will have {} entries.".format(
                    color, distinct, distinct
                )
            )

    return warnings


def _range(minimum, maximum) -> Optional[List[float]]:
    """A Plotly axis range, or None unless both ends were given.

    A half-open range is ignored rather than guessed at: Plotly needs both, and
    inventing the other end from the data would silently override the
    autoscaling the user still had.
    """
    if minimum is None or maximum is None:
        return None
    return [float(minimum), float(maximum)]


def build_scatter(df: pd.DataFrame, config: Dict) -> go.Figure:
    """``df`` plotted per ``config``.

    Raises
    ------
    ValueError
        If ``x`` or ``y`` is unset or names a column the frame doesn't have,
        if ``size`` names a non-numeric or negative-valued column, or if
        ``trendline`` is requested without statsmodels installed. All four are
        states Plotly itself fails on with a message that doesn't name the
        control that caused it.
    """
    settings = dict(DEFAULT_CONFIG)
    settings.update({k: v for k, v in config.items() if k in DEFAULT_CONFIG})

    x, y = settings["x"], settings["y"]
    if not x or not y:
        raise ValueError("Choose an X and a Y column.")

    for key in ("x", "y", "color", "symbol", "size", "hover_name", "facet_row",
                "facet_col", "error_x", "error_y"):
        column = settings.get(key)
        if column and column not in df.columns:
            raise ValueError("{} = '{}' is not a column in this sheet.".format(key, column))

    size = settings.get("size")
    if size:
        if not pd.api.types.is_numeric_dtype(df[size]):
            raise ValueError(
                "size = '{}' holds text. Marker size needs numbers - coerce the column first, "
                "or pick another.".format(size)
            )
        if (df[size].dropna() < 0).any():
            raise ValueError(
                "size = '{}' contains negative values, which Plotly cannot draw as a marker "
                "size.".format(size)
            )

    if settings.get("trendline") and not statsmodels_available():
        raise ValueError(
            "A trendline needs the statsmodels package. Install it with "
            "'pip install statsmodels', or restart via start.bat which installs "
            "requirements.txt."
        )

    kwargs: Dict = {
        "x": x,
        "y": y,
        "color": settings.get("color") or None,
        "symbol": settings.get("symbol") or None,
        "size": size or None,
        "hover_name": settings.get("hover_name") or None,
        "hover_data": list(settings.get("hover_data") or []) or None,
        "facet_row": settings.get("facet_row") or None,
        "facet_col": settings.get("facet_col") or None,
        "error_x": settings.get("error_x") or None,
        "error_y": settings.get("error_y") or None,
        "marginal_x": settings.get("marginal_x") or None,
        "marginal_y": settings.get("marginal_y") or None,
        "trendline": settings.get("trendline") or None,
        "log_x": bool(settings.get("log_x")),
        "log_y": bool(settings.get("log_y")),
        "range_x": _range(settings.get("range_x_min"), settings.get("range_x_max")),
        "range_y": _range(settings.get("range_y_min"), settings.get("range_y_max")),
        "template": settings.get("template") or None,
        "title": settings.get("title") or None,
        "opacity": settings.get("opacity"),
    }

    # Only meaningful alongside their partners, and px rejects some of them
    # when passed as None, so they are added rather than defaulted.
    if size:
        kwargs["size_max"] = int(settings.get("size_max") or 20)
    if settings.get("facet_col") and settings.get("facet_col_wrap"):
        kwargs["facet_col_wrap"] = int(settings["facet_col_wrap"])

    return px.scatter(df, **{k: v for k, v in kwargs.items() if v is not None})
