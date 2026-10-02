"""A. Scalability degradation: elapsed time and memory growth versus batch size.

One small-multiple panel per experiment (test_name), IEEE double-column width. Each language
is a clean line with small same-shape points at the measured batch sizes. Every panel carries a
data-driven callout: the speed spread at the largest shared batch (elapsed time) or the peak
(memory), so the key finding reads without decoding the axes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

from .core import BenchmarkChart, BenchmarkResults, full_test_label, languages_in, order_tests
from .theme import (IEEE_DOUBLE_COLUMN_INCHES, INK, add_figure_header, add_panel_title, format_count,
                    format_duration, language_label, language_legend_handles, line_style, note_box, save_figure)

PANEL_COLUMNS = 3
MEMORY_AXIS_MIN_SPAN_MB = 10.0  # keeps KB-level allocator noise from looking like a spike
CALLOUT_FONT_SIZE = 7.2


def annotate_speed_spread(axis: plt.Axes, test_rows: pd.DataFrame) -> None:
    """Lower-right callout: fastest vs slowest language at the largest batch every language ran."""
    coverage = test_rows.groupby("batch_size")["language"].nunique()
    largest_shared_batch = coverage[coverage == test_rows["language"].nunique()].index.max()
    final = test_rows[test_rows["batch_size"] == largest_shared_batch].set_index("language")["elapsed_seconds"]
    fastest, slowest = final.idxmin(), final.idxmax()
    text = (f"At {format_count(largest_shared_batch)} books\n"
            f"{language_label(fastest)} {format_duration(final[fastest])} · "
            f"{language_label(slowest)} {final[slowest] / final[fastest]:.1f}× slower")
    axis.text(0.97, 0.05, text, transform=axis.transAxes, ha="right", va="bottom", fontsize=CALLOUT_FONT_SIZE,
              color=INK, bbox=note_box(), zorder=6)


def annotate_peak_memory(axis: plt.Axes, test_rows: pd.DataFrame) -> None:
    """Upper-left callout: which language peaked, how high, at which batch size."""
    peak = test_rows.loc[test_rows["memory_mb"].idxmax()]
    text = f"Peak: {language_label(peak['language'])} {peak['memory_mb']:,.0f} MB\nat {format_count(peak['batch_size'])} books"
    axis.text(0.04, 0.95, text, transform=axis.transAxes, ha="left", va="top", fontsize=CALLOUT_FONT_SIZE,
              color=INK, bbox=note_box(), zorder=6)


@dataclass(frozen=True)
class ScalabilityMeasure:
    column: str
    axis_label: str
    title: str
    subtitle: str
    file_stem: str
    y_scale: str
    annotate: Callable[[plt.Axes, pd.DataFrame], None]


ELAPSED_TIME = ScalabilityMeasure(
    column="elapsed_seconds",
    axis_label="Elapsed time (log scale)",
    title="Scalability degradation: index build time vs. batch size",
    subtitle="Log–log axes: a straight line is a power law; a steeper slope degrades faster.",
    file_stem="scalability_elapsed",
    y_scale="log",
    annotate=annotate_speed_spread,
)
MEMORY_GROWTH = ScalabilityMeasure(
    column="memory_mb",
    axis_label="Memory growth during run (MB)",
    title="Scalability degradation: memory growth vs. batch size",
    subtitle="memory_mb = process memory growth (RSS delta) per batch; drops to 0 mean memory was reused after GC.",
    file_stem="scalability_memory",
    y_scale="linear",
    annotate=annotate_peak_memory,
)


class ScalabilityCharts(BenchmarkChart):
    subdirectory = "scalability"

    def render(self, results: BenchmarkResults, output_dir: Path) -> None:
        frame = results.comparable_metric("scalability")
        for measure in (ELAPSED_TIME, MEMORY_GROWTH):
            save_figure(self._draw_measure(frame, measure), output_dir, measure.file_stem)

    def _draw_measure(self, frame: pd.DataFrame, measure: ScalabilityMeasure) -> Figure:
        tests = order_tests(frame["test_name"])
        figure, axes = self._create_panel_grid(len(tests), measure)
        for panel_index, (axis, test_name) in enumerate(zip(axes, tests)):
            self._draw_test_panel(axis, frame[frame["test_name"] == test_name], measure)
            add_panel_title(axis, panel_index, full_test_label(test_name))
        for unused_axis in axes[len(tests):]:
            unused_axis.set_visible(False)
        figure.supxlabel("Batch size (books, log scale)", fontsize=9)
        figure.supylabel(measure.axis_label, fontsize=9)
        add_figure_header(figure, measure.title, measure.subtitle, language_legend_handles(languages_in(frame), "line"))
        return figure

    @staticmethod
    def _create_panel_grid(panel_count: int, measure: ScalabilityMeasure) -> tuple[Figure, list[plt.Axes]]:
        columns = min(PANEL_COLUMNS, panel_count)
        rows = math.ceil(panel_count / columns)
        shared_y = "all" if measure.y_scale == "log" else "none"
        figure, axes = plt.subplots(rows, columns, figsize=(IEEE_DOUBLE_COLUMN_INCHES, 2.45 * rows + 1.2),
                                    sharex="all", sharey=shared_y, squeeze=False, layout="constrained")
        return figure, list(axes.flat)

    def _draw_test_panel(self, axis: plt.Axes, test_rows: pd.DataFrame, measure: ScalabilityMeasure) -> None:
        for language in languages_in(test_rows):
            series = self._plottable_series(test_rows[test_rows["language"] == language], measure)
            axis.plot(series["batch_size"], series[measure.column], **line_style(language))
        self._style_axis(axis, measure)
        measure.annotate(axis, test_rows)

    @staticmethod
    def _plottable_series(language_rows: pd.DataFrame, measure: ScalabilityMeasure) -> pd.DataFrame:
        """Sorted by batch size; non-positive values are dropped on log axes (log(0) is undefined)."""
        ordered = language_rows.sort_values("batch_size")
        return ordered[ordered[measure.column] > 0] if measure.y_scale == "log" else ordered

    @staticmethod
    def _style_axis(axis: plt.Axes, measure: ScalabilityMeasure) -> None:
        axis.set_xscale("log")
        axis.xaxis.set_major_locator(LogLocator(base=10))
        axis.xaxis.set_major_formatter(FuncFormatter(format_count))
        axis.xaxis.set_minor_formatter(NullFormatter())
        axis.set_yscale(measure.y_scale)
        if measure.y_scale == "log":
            axis.yaxis.set_major_formatter(FuncFormatter(format_duration))
            axis.yaxis.set_minor_formatter(NullFormatter())
        else:
            axis.set_ylim(0, max(axis.get_ylim()[1] * 1.22, MEMORY_AXIS_MIN_SPAN_MB))  # headroom for the callout
            axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
