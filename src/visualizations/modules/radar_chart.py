"""E. Executive summary: a balanced 5-axis radar where 1.0 is the best possible outcome.

Axes: Throughput, Low latency, CPU efficiency, Transactional reliability, Developer productivity.
Memory is deliberately left out (RSS deltas are too noisy to summarise in one number; the
scalability memory chart shows them in full) and storage is covered by the Sankey diagram.

Scoring:
* Performance axes use "ratio to best": value / best (higher is better) or best / value (lower is
  better). Proportions stay honest: a 2 % gap stays a 2 % gap, unlike min-max scaling.
* Transactional reliability is an absolute success rate, 1 − (lost + duplicated) / total books,
  averaged over the recovery scenarios. It is NOT rescaled to the best language: a language that
  loses books must never be stretched to 1.0.
* Developer productivity is a hard-coded qualitative score.
Only tests measured by ALL languages enter a performance score, so no experiment biases it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .core import BenchmarkChart, BenchmarkResults, ChartDataError, order_languages, rows_shared_by_all_languages
from .theme import (GRIDLINE, INK, INK_MUTED, PLOTLY_FONT_FAMILY, SURFACE, add_figure_header, language_color,
                    language_label, language_legend_handles, rgba, save_figure, save_interactive_html)

LOGGER = logging.getLogger(__name__)

DEVELOPER_PRODUCTIVITY = {"python": 1.0, "go": 0.8, "java": 0.7, "rust": 0.4}
FILL_ALPHA = 0.18
RADAR_LINE_WIDTH = 2.5
CPU_FLOOR_PERCENT = 1.0
TITLE = "Executive summary: language trade-offs"
SUBTITLE = "1.0 = best on that axis. Performance axes: ratio to the best language; reliability: absolute success rate."


def score_higher_is_better(values: pd.Series) -> pd.Series:
    return values / values.max()


def score_lower_is_better(values: pd.Series) -> pd.Series:
    return values.min() / values


def score_as_absolute_rate(values: pd.Series) -> pd.Series:
    return values.clip(lower=0.0, upper=1.0)


def geometric_mean_by_language(frame: pd.DataFrame, column: str) -> pd.Series:
    """Geometric mean across tests: the standard way to average rates/latencies (SPEC-style),
    so one large-valued test cannot dominate the composite."""
    positive = frame[column].clip(lower=np.finfo(float).tiny)
    return np.exp(np.log(positive).groupby(frame["language"]).mean())


def measure_throughput(results: BenchmarkResults) -> pd.Series:
    shared = rows_shared_by_all_languages(results.comparable_metric("throughput"), ["test_name"])
    return geometric_mean_by_language(shared, "items_per_second")


def measure_latency(results: BenchmarkResults) -> pd.Series:
    shared = rows_shared_by_all_languages(results.comparable_metric("statistics"), ["test_name"])
    return geometric_mean_by_language(shared, "mean_seconds")


def measure_mean_cpu(results: BenchmarkResults) -> pd.Series:
    shared = rows_shared_by_all_languages(results.comparable_metric("scalability"), ["test_name", "batch_size"])
    return shared.groupby("language")["cpu_percent"].mean().clip(lower=CPU_FLOOR_PERCENT)


def measure_reliability(results: BenchmarkResults) -> pd.Series:
    """Share of books processed exactly once after an interrupted run, averaged over scenarios."""
    recovery = results.comparable_metric("recovery")
    faulty_books = (recovery["lost"] + recovery["duplicated"]).clip(lower=0)
    success_rate = (1 - faulty_books / recovery["total_books"]).clip(lower=0.0, upper=1.0)
    return success_rate.groupby(recovery["language"]).mean()


def measure_productivity(results: BenchmarkResults) -> pd.Series:
    return pd.Series(DEVELOPER_PRODUCTIVITY, dtype=float).reindex(list(results.languages))


@dataclass(frozen=True)
class RadarAxis:
    title: str
    raw_unit: str
    measure: Callable[[BenchmarkResults], pd.Series]
    score: Callable[[pd.Series], pd.Series]


RADAR_AXES = (
    RadarAxis("Throughput", "items/s, geometric mean", measure_throughput, score_higher_is_better),
    RadarAxis("Low latency", "s per operation, geometric mean", measure_latency, score_lower_is_better),
    RadarAxis("CPU efficiency", "mean CPU %", measure_mean_cpu, score_lower_is_better),
    RadarAxis("Transactional reliability", "books processed exactly once", measure_reliability, score_as_absolute_rate),
    RadarAxis("Developer productivity", "qualitative score", measure_productivity, score_as_absolute_rate),
)


@dataclass(frozen=True)
class RadarTable:
    raw_values: pd.DataFrame
    scores: pd.DataFrame

    @property
    def axis_titles(self) -> list[str]:
        return [axis.title for axis in RADAR_AXES]


def build_radar_table(results: BenchmarkResults) -> RadarTable:
    """Raw composite per axis, then per-axis scores; languages missing any axis are excluded."""
    raw_values = pd.DataFrame({axis.title: axis.measure(results) for axis in RADAR_AXES})
    complete = raw_values.dropna()
    excluded = sorted(set(raw_values.index) - set(complete.index))
    if excluded:
        LOGGER.warning("Radar: %s excluded (missing data on at least one axis).", ", ".join(excluded))
    if complete.empty:
        raise ChartDataError("No language has data on all five radar axes.")
    complete = complete.loc[order_languages(complete.index)]
    scores = pd.DataFrame({axis.title: axis.score(complete[axis.title]) for axis in RADAR_AXES})
    return RadarTable(raw_values=complete, scores=scores)


class ExecutiveRadar(BenchmarkChart):
    subdirectory = "radar"

    def render(self, results: BenchmarkResults, output_dir: Path) -> None:
        table = build_radar_table(results)
        self._write_score_table(table, output_dir)
        save_figure(StaticRadarFigure(table).draw(), output_dir, "executive_radar")
        save_interactive_html(InteractiveRadarFigure(table).build(), output_dir, "executive_radar")

    @staticmethod
    def _write_score_table(table: RadarTable, output_dir: Path) -> None:
        units = {axis.title: axis.raw_unit for axis in RADAR_AXES}
        raw = table.raw_values.rename(columns=lambda title: f"raw {title} [{units[title]}]")
        scores = table.scores.rename(columns=lambda title: f"score {title}")
        output_dir.mkdir(parents=True, exist_ok=True)
        pd.concat([raw, scores], axis=1).rename_axis("language").to_csv(output_dir / "radar_scores.csv",
                                                                         float_format="%.6g")


class StaticRadarFigure:
    """Matplotlib radar for SVG/PDF/PNG (no browser or kaleido needed)."""

    def __init__(self, table: RadarTable) -> None:
        self.table = table
        self.angles = np.linspace(0, 2 * np.pi, len(table.axis_titles), endpoint=False)

    def draw(self) -> plt.Figure:
        figure, axis = plt.subplots(figsize=(6.2, 6.6), subplot_kw={"projection": "polar"}, layout="constrained")
        self._style_polar_axis(axis)
        for language in self._languages_by_area():
            self._draw_polygon(axis, language)
        legend = language_legend_handles(list(self.table.scores.index), "line")
        add_figure_header(figure, TITLE, SUBTITLE, legend)
        return figure

    def _languages_by_area(self) -> list[str]:
        """Largest polygons first, so smaller ones stay visible on top."""
        return list(self.table.scores.mean(axis=1).sort_values(ascending=False).index)

    def _draw_polygon(self, axis: plt.Axes, language: str) -> None:
        values = self.table.scores.loc[language, self.table.axis_titles].to_numpy()
        closed_angles = np.append(self.angles, self.angles[0])
        closed_values = np.append(values, values[0])
        color = language_color(language)
        axis.fill(closed_angles, closed_values, color=color, alpha=FILL_ALPHA, zorder=2)
        axis.plot(closed_angles, closed_values, color=color, linewidth=RADAR_LINE_WIDTH, zorder=3,
                  marker="o", markersize=4, markeredgecolor=SURFACE, markeredgewidth=0.6, label=language_label(language))

    def _style_polar_axis(self, axis: plt.Axes) -> None:
        axis.set_theta_offset(np.pi / 2)
        axis.set_theta_direction(-1)
        axis.set_ylim(0, 1.0)
        axis.set_yticks([0.25, 0.5, 0.75, 1.0], ["0.25", "0.50", "0.75", ""], fontsize=7.5, color=INK_MUTED)
        axis.set_rlabel_position(180)  # straight down, between two axes, away from the axis labels
        for radial_label in axis.get_yticklabels():
            radial_label.set_bbox(dict(boxstyle="round,pad=0.15", facecolor=SURFACE, edgecolor="none", alpha=0.85))
            radial_label.set_zorder(6)
        axis.set_xticks(self.angles, [self._wrapped(title) for title in self.table.axis_titles],
                        fontsize=9.5, color=INK, fontweight="bold")
        axis.tick_params(axis="x", pad=26)
        axis.grid(color=GRIDLINE, linewidth=0.7)
        axis.spines["polar"].set_color(INK)
        axis.spines["polar"].set_linewidth(1.0)

    @staticmethod
    def _wrapped(title: str) -> str:
        return title.replace(" ", "\n", 1)


class InteractiveRadarFigure:
    """Plotly radar: hover shows each score with its raw value; click legend entries to isolate."""

    def __init__(self, table: RadarTable) -> None:
        self.table = table
        self.units = {axis.title: axis.raw_unit for axis in RADAR_AXES}

    def build(self) -> go.Figure:
        figure = go.Figure([self._language_trace(language) for language in self.table.scores.index])
        figure.update_layout(**self._layout())
        return figure

    def _language_trace(self, language: str) -> go.Scatterpolar:
        titles = self.table.axis_titles
        scores = self.table.scores.loc[language, titles].tolist()
        raw_text = [f"{self.table.raw_values.at[language, title]:,.4g} ({self.units[title]})" for title in titles]
        return go.Scatterpolar(
            r=scores + scores[:1], theta=titles + titles[:1], name=language_label(language),
            fill="toself", fillcolor=rgba(language_color(language), FILL_ALPHA),
            line=dict(color=language_color(language), width=RADAR_LINE_WIDTH),
            marker=dict(size=7, color=language_color(language), line=dict(color=SURFACE, width=1.5)),
            customdata=raw_text + raw_text[:1],
            hovertemplate="<b>%{fullData.name}</b> · %{theta}<br>score %{r:.2f}<br>raw %{customdata}<extra></extra>",
        )

    @staticmethod
    def _layout() -> dict:
        return dict(
            title=dict(text=f"<b>{TITLE}</b><br><i><span style='font-size:14px;color:{INK_MUTED}'>{SUBTITLE}</span></i>",
                       x=0.03, xanchor="left", y=0.965, font=dict(size=24, color=INK)),
            polar=dict(
                bgcolor=SURFACE, domain=dict(x=[0.1, 0.9], y=[0.07, 0.85]),
                radialaxis=dict(range=[0, 1], tickvals=[0.25, 0.5, 0.75], ticktext=["0.25", "0.50", "0.75"],
                                angle=270, tickangle=-90,  # straight down, between two axes
                                gridcolor=GRIDLINE, linecolor=GRIDLINE, tickfont=dict(size=12, color=INK_MUTED)),
                angularaxis=dict(rotation=90, direction="clockwise", gridcolor=GRIDLINE, linecolor=INK, linewidth=1.4,
                                 ticks="outside", ticklen=18, tickcolor="rgba(0,0,0,0)",
                                 tickfont=dict(size=17, color=INK)),
            ),
            legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.02, font=dict(size=16)),
            font=dict(family=PLOTLY_FONT_FAMILY, color=INK), paper_bgcolor=SURFACE,
            width=1100, height=880, margin=dict(l=40, r=40, t=125, b=60),
            hoverlabel=dict(font=dict(family=PLOTLY_FONT_FAMILY, size=14)),
        )
