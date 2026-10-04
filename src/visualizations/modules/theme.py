"""Design system shared by every chart: IEEE/ACM-style typography, axes, palette and file output.

Look: Times-class serif type (matches an IEEE/ACM paper body), a full black frame with
inside ticks on all four sides plus minor ticks, a hairline grid, bold titles, (a)/(b)/(c)
panel tags and a fixed figure width equal to the IEEE double-column text width (7.16 in),
so figures drop into LaTeX at 1:1 scale with 8-9 pt text.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # headless rendering: no display needed (CI, servers, WSL)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.artist import Artist  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402

LOGGER = logging.getLogger(__name__)

LANGUAGE_COLORS = {
    "python": "#1F4E79",  # dark classic blue
    "java": "#C0392B",    # classic cup red
    "go": "#00ACC1",      # vibrant cyan
    "rust": "#E67E22",    # warm amber / orange
}
LANGUAGE_LABELS = {"python": "Python", "java": "Java", "go": "Go", "rust": "Rust"}
FALLBACK_COLOR = "#7F8C8D"

INK = "#111111"            # frame, ticks, titles: near-black for print contrast
INK_SECONDARY = "#3D4451"
INK_MUTED = "#6B7280"
GRIDLINE = "#E3E6EA"
ROW_BAND = "#F3F5F8"
SURFACE = "#FFFFFF"
BAR_EDGE = "#1A1A1A"

SERIF_STACK = ["Times New Roman", "TeX Gyre Termes", "Nimbus Roman", "STIXGeneral", "Liberation Serif", "DejaVu Serif"]
PLOTLY_FONT_FAMILY = "'Times New Roman', 'TeX Gyre Termes', 'Nimbus Roman', 'STIX Two Text', serif"

IEEE_DOUBLE_COLUMN_INCHES = 7.16
LINE_WIDTH = 1.8
POINT_SIZE = 3.6  # small same-shape dots with a white halo: they mark measured points without clutter
STATIC_FORMATS = ("svg", "pdf", "png")
PNG_DPI = 300
PANEL_TAGS = "abcdefghijklmnopqrstuvwxyz"

TITLE_BAND_INCHES = 0.30
SUBTITLE_BAND_INCHES = 0.22
LEGEND_BAND_INCHES = 0.27
RULE_GAP_INCHES = 0.08
TOP_PADDING_INCHES = 0.04

MATPLOTLIB_STYLE = {
    "font.family": "serif", "font.serif": SERIF_STACK, "mathtext.fontset": "stix", "font.size": 8.5,
    "text.color": INK, "axes.labelcolor": INK, "axes.titlecolor": INK,
    "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 5,
    "axes.labelsize": 9, "axes.labelpad": 4,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": INK, "axes.linewidth": 0.8,
    "axes.spines.top": True, "axes.spines.right": True,
    "axes.grid": True, "axes.grid.which": "major", "axes.axisbelow": True,
    "grid.color": GRIDLINE, "grid.linewidth": 0.5, "grid.linestyle": "-",
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    "xtick.minor.visible": True, "ytick.minor.visible": True,
    "xtick.major.size": 3.5, "ytick.major.size": 3.5, "xtick.minor.size": 1.8, "ytick.minor.size": 1.8,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8, "xtick.minor.width": 0.6, "ytick.minor.width": 0.6,
    "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "xtick.major.pad": 4, "ytick.major.pad": 4,
    "legend.frameon": False, "legend.fontsize": 8.5,
    "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    "svg.fonttype": "none", "svg.hashsalt": "boogle-engine",
    "pdf.fonttype": 42, "ps.fonttype": 42,
}


def language_color(language: str) -> str:
    return LANGUAGE_COLORS.get(language, FALLBACK_COLOR)


def language_label(language: str) -> str:
    return LANGUAGE_LABELS.get(language, language.capitalize())


def rgba(hex_color: str, alpha: float) -> str:
    """'#1F4E79', 0.4 -> 'rgba(31,78,121,0.4)' for Plotly fills and links."""
    digits = hex_color.lstrip("#")
    red, green, blue = (int(digits[offset:offset + 2], 16) for offset in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def apply_matplotlib_theme() -> None:
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    plt.rcParams.update(MATPLOTLIB_STYLE)


def line_style(language: str) -> dict:
    """Clean line with small same-shape points (no squares/triangles/diamonds)."""
    return dict(color=language_color(language), linewidth=LINE_WIDTH, marker="o", markersize=POINT_SIZE,
                markerfacecolor=language_color(language), markeredgecolor=SURFACE, markeredgewidth=0.6,
                label=language_label(language), zorder=3)


def language_legend_handles(languages: Sequence[str], mark: str) -> list[Artist]:
    """Legend keys that repeat the chart's own mark: 'line', 'bar' or 'dot'."""
    if mark == "bar":
        return [Patch(facecolor=language_color(lang), edgecolor=BAR_EDGE, linewidth=0.6, label=language_label(lang))
                for lang in languages]
    if mark == "dot":
        return [Line2D([], [], linestyle="none", marker="o", markersize=6.5, color=language_color(lang),
                       markeredgecolor=SURFACE, label=language_label(lang)) for lang in languages]
    return [Line2D([], [], color=language_color(lang), linewidth=LINE_WIDTH + 0.6, label=language_label(lang))
            for lang in languages]


def add_figure_header(figure: Figure, title: str, subtitle: str = "", legend_handles: Sequence[Artist] = ()) -> None:
    """Bold title, italic subtitle, legend row and a hairline rule, in a reserved band above the panels."""
    band_inches = TOP_PADDING_INCHES + TITLE_BAND_INCHES + RULE_GAP_INCHES
    band_inches += SUBTITLE_BAND_INCHES if subtitle else 0.0
    band_inches += LEGEND_BAND_INCHES if legend_handles else 0.0
    reserve_top_band(figure, band_inches)
    cursor = 1 - TOP_PADDING_INCHES / figure.get_figheight()
    figure.text(0.008, cursor, title, ha="left", va="top", fontsize=12.5, fontweight="bold", color=INK)
    cursor -= TITLE_BAND_INCHES / figure.get_figheight()
    if subtitle:
        figure.text(0.008, cursor, subtitle, ha="left", va="top", fontsize=8.8, fontstyle="italic", color=INK_MUTED)
        cursor -= SUBTITLE_BAND_INCHES / figure.get_figheight()
    if legend_handles:
        figure.legend(handles=list(legend_handles), loc="upper left", bbox_to_anchor=(0.004, cursor),
                      ncol=len(legend_handles), borderaxespad=0, handlelength=1.8, handletextpad=0.5, columnspacing=1.8)
        cursor -= LEGEND_BAND_INCHES / figure.get_figheight()
    add_header_rule(figure, cursor - RULE_GAP_INCHES / 3 / figure.get_figheight())


def reserve_top_band(figure: Figure, band_inches: float) -> None:
    figure.get_layout_engine().set(rect=(0, 0, 1, 1 - band_inches / figure.get_figheight()))


def add_header_rule(figure: Figure, height: float) -> None:
    figure.add_artist(Line2D([0.008, 0.992], [height, height], transform=figure.transFigure, color=INK, linewidth=0.9))


def add_figure_footnote(figure: Figure, text: str) -> None:
    """Italic footnote below the figure; `bbox_inches='tight'` grows the canvas to include it."""
    figure.text(0.008, -0.01, text, ha="left", va="top", fontsize=7.6, fontstyle="italic", color=INK_MUTED, wrap=True)


def add_panel_title(axis: plt.Axes, panel_index: int, title: str) -> None:
    """IEEE-style sub-figure title: '(a) JSON file index build'."""
    axis.set_title(f"({PANEL_TAGS[panel_index]}) {title}")


def style_categorical_axis(axis: plt.Axes, axis_name: str) -> None:
    """Category axes keep their labels but drop ticks and minor ticks (they carry no scale)."""
    axis.tick_params(axis=axis_name, which="both", length=0)
    axis.grid(axis=axis_name, visible=False)
    getattr(axis, f"{axis_name}axis").set_minor_locator(NullLocator())


def emphasis_weight(value: float, best_value: float) -> str:
    """Bold for the winning value of a group, normal otherwise."""
    return "bold" if value == best_value else "normal"


def note_box() -> dict:
    return dict(boxstyle="round,pad=0.35", facecolor=SURFACE, edgecolor="#9AA1AC", linewidth=0.6)


def save_figure(figure: Figure, output_dir: Path, stem: str) -> None:
    """Write SVG (vector editing), PDF (LaTeX) and PNG (preview) versions of a figure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in STATIC_FORMATS:
        figure.savefig(output_dir / f"{stem}.{extension}", dpi=PNG_DPI, bbox_inches="tight",
                       pad_inches=0.06, metadata=_reproducible_metadata(extension))
    plt.close(figure)
    LOGGER.info("Wrote %s.{%s}", output_dir / stem, ",".join(STATIC_FORMATS))


def _reproducible_metadata(extension: str) -> dict[str, None]:
    """Drop creation dates so re-running on the same data yields byte-identical vectors."""
    return {"svg": {"Date": None}, "pdf": {"CreationDate": None}}.get(extension, {})


def save_interactive_html(figure, output_dir: Path, stem: str) -> None:
    """Self-contained HTML (plotly.js embedded, works offline). The camera button exports SVG."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{stem}.html"
    figure.write_html(path, include_plotlyjs=True, full_html=True, config={
        "displaylogo": False,
        "toImageButtonOptions": {"format": "svg", "filename": stem},
    })
    LOGGER.info("Wrote %s", path)


def format_duration(seconds: float, _tick_position: int = 0) -> str:
    """Tick formatter: 2e-5 -> '20 µs', 0.1 -> '100 ms', 1181 -> '1,181 s'."""
    if seconds <= 0:
        return ""
    for unit, scale in (("s", 1.0), ("ms", 1e-3), ("µs", 1e-6), ("ns", 1e-9)):
        if seconds >= scale * 0.999:
            return f"{_three_significant_digits(seconds / scale)} {unit}"
    return f"{seconds:.0e} s"


def _three_significant_digits(value: float) -> str:
    """1000 -> '1,000' (never '1e+03'), 4.587 -> '4.59', 23.4 -> '23.4'."""
    return f"{value:,.0f}" if value >= 100 else f"{value:.3g}"


def format_count(value: float, _tick_position: int = 0) -> str:
    """Tick formatter: 10 -> '10', 1000 -> '1k', 10000 -> '10k'."""
    return f"{value / 1000:g}k" if value >= 1000 else f"{value:g}"


def format_rate(value: float) -> str:
    """Bar labels with sensible precision: 2.61, 25.8, 120."""
    if value < 10:
        return f"{value:.2f}"
    return f"{value:.1f}" if value < 100 else f"{value:.0f}"
