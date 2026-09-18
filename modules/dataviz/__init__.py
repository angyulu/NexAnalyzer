"""
Plot Explorer: an arbitrary spreadsheet, plotted.

Deliberately schema-blind. Nothing in this package knows what a peak is, what
a material preset is, or what NexAnalyzer's own .xlsx export looks like — it
reads whatever columns a sheet happens to have and hands them to
plotly.express.scatter. That ignorance is the feature: the spreadsheets worth
plotting here are lab notebooks kept by hand, and a reader that expected a
known schema would refuse most of them.

It sits under `modules/` rather than `core/` despite knowing nothing about
spectra, because `core` is the plumbing other packages import and nothing will
ever import this. See docs/Summary.md, "The one rule".
"""
