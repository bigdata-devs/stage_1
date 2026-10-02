"""C. Latency and jitter: mean latency with ±1 standard-deviation error bars.

A horizontal dot-and-error-bar chart (Cleveland style): test names read left to right without
wrapping, each language sits in its own lane inside a test row, and the shared log-scaled x-axis
keeps microsecond lookups and millisecond queries comparable. The fastest language of each test
is labelled in bold. Only tests measured by 2+ languages reach this chart.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, NullFormatter

from .core import (BenchmarkChart, BenchmarkResults, TestStage, group_tests_by_stage, languages_in,
                   short_test_label)
from .theme import (IEEE_DOUBLE_COLUMN_INCHES, INK, ROW_BAND, SURFACE, add_figure_footnote, add_figure_header,
                    add_panel_title, emphasis_weight, format_duration, language_color, language_legend_handles,
                    save_figure, style_categorical_axis)

LATENCY_STAGES = (
    TestStage("Datalake lookups", r"^lookup_"),
    TestStage("Inverted-index queries", r"^query_.*_index$"),
    TestStage("Metadata queries", r"^query_.*_sqlite$"),
)
LANE_SPACING = 0.2
INCHES_PER_TEST_ROW = 0.62
TIME_FLOOR_SECONDS = 5e-7  # a log axis cannot show 0 s (timer-resolution minimums)
VALUE_LABEL_GAP = 1.2      # multiplicative gap on a log axis between bar end and its label
TITLE = "Query and lookup latency with jitter (lower is better)"
SUBTITLE = "Dot = mean latency per operation; whiskers = ±1 standard deviation. Bold label = fastest language."


class LatencyChart(BenchmarkChart):
    subdirectory = "latency"

    def render(self, results: BenchmarkResults, output_dir: Path) -> None:
        frame = self._with_error_bounds(results.comparable_metric("statistics"))
        stages = group_tests_by_stage(frame["test_name"].unique(), LATENCY_STAGES)
        figure, axes = self._create_stage_rows(stages, frame)
        for panel_index, (axis, (stage, tests)) in enumerate(zip(axes, stages)):
            self._draw_stage(axis, frame[frame["test_name"].isin(tests)], tests)
            add_panel_title(axis, panel_index, stage.title)
        self._style_shared_x_axis(axes, frame)
        add_figure_header(figure, TITLE, SUBTITLE, language_legend_handles(languages_in(frame), "dot"))
        add_figure_footnote(figure, self._footnote(frame))
        save_figure(figure, output_dir, "latency")

    @staticmethod
    def _with_error_bounds(frame: pd.DataFrame) -> pd.DataFrame:
        """Latency is right-skewed, so mean − SD is often negative: the lower whisker is clipped at the
        fastest observed run (min_seconds), which is the honest lower limit of the distribution."""
        plotted_mean = frame["mean_seconds"].clip(lower=TIME_FLOOR_SECONDS)
        lower_bound = np.maximum(frame["mean_seconds"] - frame["stdev_seconds"], frame["min_seconds"])
        return frame.assign(plotted_mean=plotted_mean,
                            lower_bound=lower_bound.clip(lower=TIME_FLOOR_SECONDS).clip(upper=plotted_mean),
                            upper_bound=plotted_mean + frame["stdev_seconds"])

    def _create_stage_rows(self, stages: list[tuple[TestStage, list[str]]],
                           frame: pd.DataFrame) -> tuple[plt.Figure, list[plt.Axes]]:
        height_ratios = [self._stage_height(frame[frame["test_name"].isin(tests)], frame) for _, tests in stages]
        figure_height = INCHES_PER_TEST_ROW * sum(height_ratios) + 0.4 * len(stages) + 1.4
        figure, axes = plt.subplots(len(stages), 1, figsize=(IEEE_DOUBLE_COLUMN_INCHES, figure_height), sharex="all",
                                    squeeze=False, gridspec_kw={"height_ratios": height_ratios}, layout="constrained")
        return figure, list(axes.flat)

    @staticmethod
    def _stage_height(stage_rows: pd.DataFrame, frame: pd.DataFrame) -> float:
        """Rows only need as many lanes as languages that ran the stage."""
        language_share = stage_rows["language"].nunique() / frame["language"].nunique()
        return stage_rows["test_name"].nunique() * (0.4 + 0.6 * language_share)

    def _draw_stage(self, axis: plt.Axes, stage_rows: pd.DataFrame, tests: list[str]) -> None:
        for row_position, test_name in enumerate(tests):
            if row_position % 2 == 0:
                axis.axhspan(row_position - 0.5, row_position + 0.5, color=ROW_BAND, linewidth=0, zorder=0)
            self._draw_test_row(axis, stage_rows[stage_rows["test_name"] == test_name], row_position)
        axis.set_yticks(range(len(tests)), [short_test_label(test) for test in tests])
        axis.set_ylim(len(tests) - 0.5, -0.5)
        style_categorical_axis(axis, "y")

    @staticmethod
    def _draw_test_row(axis: plt.Axes, test_rows: pd.DataFrame, row_position: int) -> None:
        languages = languages_in(test_rows)
        fastest_mean = test_rows["mean_seconds"].min()
        lane_offsets = (np.arange(len(languages)) - (len(languages) - 1) / 2) * LANE_SPACING
        for language, lane_offset in zip(languages, lane_offsets):
            row = test_rows[test_rows["language"] == language].iloc[0]
            lane = row_position + lane_offset
            axis.errorbar(row["plotted_mean"], lane, xerr=[[row["plotted_mean"] - row["lower_bound"]],
                                                           [row["upper_bound"] - row["plotted_mean"]]],
                          fmt="o", color=language_color(language), markersize=6, markeredgecolor=SURFACE,
                          markeredgewidth=0.9, elinewidth=1.5, capsize=2.4, capthick=1.2, zorder=3)
            axis.text(row["upper_bound"] * VALUE_LABEL_GAP, lane, format_duration(row["mean_seconds"]), va="center",
                      ha="left", fontsize=7, color=INK, fontweight=emphasis_weight(row["mean_seconds"], fastest_mean))

    @staticmethod
    def _style_shared_x_axis(axes: list[plt.Axes], frame: pd.DataFrame) -> None:
        axes[0].set_xscale("log")
        axes[0].set_xlim(frame["lower_bound"].min() / 2, frame["upper_bound"].max() * 9)
        axes[-1].xaxis.set_major_formatter(FuncFormatter(format_duration))
        axes[-1].xaxis.set_minor_formatter(NullFormatter())
        axes[-1].set_xlabel("Mean latency per operation (log scale)")

    @staticmethod
    def _footnote(frame: pd.DataFrame) -> str:
        note = "Lower whiskers are clipped at the fastest observed run: latency is right-skewed, so mean − SD can be negative."
        if (frame["min_seconds"] < TIME_FLOOR_SECONDS).any():
            note += f" Minimums reported as 0 s (below timer resolution) are drawn at {format_duration(TIME_FLOOR_SECONDS)}."
        return note
