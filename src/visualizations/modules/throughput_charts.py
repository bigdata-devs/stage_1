"""B. Throughput comparison: grouped bars of items per second, one panel per pipeline stage.

Stages differ by up to 30× (≈2 books/s for download + write vs ≈75 books/s for datalake writes),
so each stage gets its own panel and y-scale instead of squashing the small bars. Bars carry crisp
dark borders and a value label at the tip; the winner of each group is labelled in bold.
Only tests measured by 2+ languages reach this chart; inside a group, bars are re-centred on the
languages that actually ran it (e.g. three bars for tokenization), so there are never empty slots.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .core import (BenchmarkChart, BenchmarkResults, TestStage, group_tests_by_stage, languages_in,
                   languages_measuring, short_test_label)
from .theme import (BAR_EDGE, IEEE_DOUBLE_COLUMN_INCHES, INK, add_figure_header, add_panel_title, emphasis_weight,
                    format_rate, language_color, language_legend_handles, save_figure, style_categorical_axis)

THROUGHPUT_STAGES = (
    TestStage("Datalake writes", r"^write_throughput_"),
    TestStage("Download + write", r"^download_"),
    TestStage("Tokenization", r"^tokenize_"),
    TestStage("Metadata inserts", r"^insert_throughput_"),
)
BAR_WIDTH = 0.19
MIN_PANEL_WIDTH_RATIO = 1.25
HEADROOM = 1.18  # space above the tallest bar for its value label
TITLE = "Throughput by pipeline stage (higher is better)"
SUBTITLE = "Items processed per second; each panel has its own scale. Bold label = fastest language in the group."


class ThroughputChart(BenchmarkChart):
    subdirectory = "throughput"

    def render(self, results: BenchmarkResults, output_dir: Path) -> None:
        frame = results.comparable_metric("throughput")
        stages = group_tests_by_stage(frame["test_name"].unique(), THROUGHPUT_STAGES)
        figure, axes = self._create_stage_panels(stages)
        for panel_index, (axis, (stage, tests)) in enumerate(zip(axes, stages)):
            self._draw_stage(axis, frame[frame["test_name"].isin(tests)], tests)
            add_panel_title(axis, panel_index, stage.title)
        axes[0].set_ylabel("Throughput (items / s)")
        add_figure_header(figure, TITLE, SUBTITLE, language_legend_handles(languages_in(frame), "bar"))
        save_figure(figure, output_dir, "throughput")

    @staticmethod
    def _create_stage_panels(stages: list[tuple[TestStage, list[str]]]) -> tuple[plt.Figure, list[plt.Axes]]:
        width_ratios = [max(len(tests), MIN_PANEL_WIDTH_RATIO) for _, tests in stages]
        figure, axes = plt.subplots(1, len(stages), figsize=(IEEE_DOUBLE_COLUMN_INCHES, 3.45), squeeze=False,
                                    gridspec_kw={"width_ratios": width_ratios}, layout="constrained")
        return figure, list(axes.flat)

    def _draw_stage(self, axis: plt.Axes, stage_rows: pd.DataFrame, tests: list[str]) -> None:
        for group_position, test_name in enumerate(tests):
            self._draw_bar_group(axis, stage_rows[stage_rows["test_name"] == test_name], group_position)
        axis.set_xticks(range(len(tests)), [short_test_label(test) for test in tests])
        axis.set_xlim(-0.55, len(tests) - 0.45)
        axis.set_ylim(0, stage_rows["items_per_second"].max() * HEADROOM)
        style_categorical_axis(axis, "x")

    @staticmethod
    def _draw_bar_group(axis: plt.Axes, test_rows: pd.DataFrame, group_position: int) -> None:
        languages = languages_measuring(test_rows, test_rows["test_name"].iloc[0])
        values = test_rows.groupby("language")["items_per_second"].mean()
        offsets = (np.arange(len(languages)) - (len(languages) - 1) / 2) * BAR_WIDTH
        for language, offset in zip(languages, offsets):
            axis.bar(group_position + offset, values[language], width=BAR_WIDTH, color=language_color(language),
                     edgecolor=BAR_EDGE, linewidth=0.6, zorder=3)
            axis.annotate(format_rate(values[language]), (group_position + offset, values[language]),
                          xytext=(0, 2.5), textcoords="offset points", ha="center", va="bottom", fontsize=6.8,
                          color=INK, fontweight=emphasis_weight(values[language], values.max()), zorder=5)
