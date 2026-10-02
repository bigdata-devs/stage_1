"""D. Storage flow: Raw corpus → Datalake layouts → Inverted-index stores (interactive Sankey).

Link width is the size on disk (MB). The indexer reads the shared corpus rather than one
specific layout, so every index's size is split evenly across the datalake layouts that can
feed it. Nodes are placed explicitly in three spaced columns and labelled with annotations
placed outside the flows (left of the corpus, above each layout, right of each index), so no
label sits on top of a link. Buttons switch between languages.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from .core import BenchmarkChart, BenchmarkResults, ChartDataError, languages_in
from .theme import (INK, INK_MUTED, INK_SECONDARY, PLOTLY_FONT_FAMILY, SURFACE, language_label, rgba,
                    save_interactive_html)

FIGURE_WIDTH, FIGURE_HEIGHT = 1400, 800
MARGIN = dict(l=40, r=40, t=180, b=90)
PLOT_HEIGHT_PX = FIGURE_HEIGHT - MARGIN["t"] - MARGIN["b"]
DOMAIN_X = (0.14, 0.78)  # free space left of the corpus and right of the indexes for labels
NODE_THICKNESS = 24
NODE_PAD_PX = 52
LINK_OPACITY = 0.4
COLUMN_X = {"Raw": 0.0005, "Datalake": 0.5, "Index": 0.9995}
COLUMN_HEADERS = {"Raw": "RAW CORPUS", "Datalake": "DATALAKE LAYOUTS", "Index": "INVERTED-INDEX STORES"}
NODE_COLORS = {
    ("Raw", "Raw corpus"): "#37474F",
    ("Datalake", "Time-based"): "#2E7D32",
    ("Datalake", "Book-based"): "#43A047",
    ("Datalake", "Batch-based"): "#8BC34A",
    ("Index", "JSON file"): "#4527A0",
    ("Index", "Folder"): "#7B1FA2",
    ("Index", "MongoDB"): "#BA68C8",
}
FALLBACK_NODE_COLOR = "#90A4AE"
DATALAKE_ORDER = ("Time-based", "Book-based", "Batch-based")
INDEX_ORDER = ("JSON file", "Folder", "MongoDB")
FOOTNOTE = ("Link width = size on disk (MB). Each index is split evenly across the datalake layouts, because the "
            "indexer reads the shared corpus rather than one layout.<br>Indexes hold up to 10k synthetic books and "
            "the datalake 100 real books, so the size jump is not a per-book amplification ratio.")


@dataclass(frozen=True)
class StorageNode:
    layer: str
    name: str
    size_mb: float
    file_count: int
    flow_mb: float  # node height in the diagram = max(inflow, outflow)

    @property
    def color(self) -> str:
        return NODE_COLORS.get((self.layer, self.name), FALLBACK_NODE_COLOR)


@dataclass(frozen=True)
class StorageFlow:
    """Nodes (column order) and links of one language's storage diagram."""

    language: str
    nodes: list[StorageNode]
    links: list[tuple[int, int, float]]

    @property
    def total_index_mb(self) -> float:
        return sum(node.size_mb for node in self.nodes if node.layer == "Index")


def build_storage_flow(language: str, language_rows: pd.DataFrame) -> StorageFlow:
    datalake = language_rows[language_rows["storage_layer"] == "Datalake"].sort_values("storage_component")
    indexes = language_rows[language_rows["storage_layer"] == "Index"].sort_values("storage_component")
    if datalake.empty or indexes.empty:
        raise ChartDataError(f"{language}: disk_usage.csv needs both datalake and index rows.")
    index_share = indexes["size_mb"].sum() / len(datalake)
    raw = StorageNode("Raw", "Raw corpus", datalake["size_mb"].sum(), 0, datalake["size_mb"].sum())
    layouts = [_node(row, max(row.size_mb, index_share)) for row in _ordered_rows(datalake, DATALAKE_ORDER)]
    stores = [_node(row, row.size_mb) for row in _ordered_rows(indexes, INDEX_ORDER)]
    links = [(0, 1 + position, layout.size_mb) for position, layout in enumerate(layouts)]
    links += [(1 + source, 1 + len(layouts) + target, store.size_mb / len(layouts))
              for source in range(len(layouts)) for target, store in enumerate(stores)]
    return StorageFlow(language, [raw, *layouts, *stores], links)



def _ordered_rows(rows: pd.DataFrame, preferred_order: tuple[str, ...]) -> list:
    rank = {name: position for position, name in enumerate(preferred_order)}
    return sorted(rows.itertuples(index=False), key=lambda row: (rank.get(row.storage_component, len(rank)),
                                                                 row.storage_component))


def _node(row, flow_mb: float) -> StorageNode:
    return StorageNode(row.storage_layer, row.storage_component, float(row.size_mb), int(row.file_count), flow_mb)


class NodeLayout:
    """Reproduces Plotly's node scaling so nodes can be pinned to evenly spaced columns and
    their labels placed precisely next to them (positions are fractions of the plot area)."""

    def __init__(self, flow: StorageFlow) -> None:
        self.flow = flow
        columns = [[node for node in flow.nodes if node.layer == layer] for layer in COLUMN_X]
        self.pixels_per_mb = min((PLOT_HEIGHT_PX - (len(column) - 1) * NODE_PAD_PX) / sum(n.flow_mb for n in column)
                                 for column in columns if column)

    def height_fraction(self, node: StorageNode) -> float:
        return node.flow_mb * self.pixels_per_mb / PLOT_HEIGHT_PX

    def center_fraction(self, node: StorageNode) -> float:
        """Vertical centre measured from the top (0) to the bottom (1); each column is centred."""
        column = [other for other in self.flow.nodes if other.layer == node.layer]
        pad = NODE_PAD_PX / PLOT_HEIGHT_PX
        column_height = sum(self.height_fraction(other) for other in column) + pad * (len(column) - 1)
        above = column[:column.index(node)]
        offset = (1 - column_height) / 2 + sum(self.height_fraction(other) + pad for other in above)
        return offset + self.height_fraction(node) / 2

    @staticmethod
    def paper_x(node: StorageNode) -> float:
        return DOMAIN_X[0] + COLUMN_X[node.layer] * (DOMAIN_X[1] - DOMAIN_X[0])


class StorageSankey(BenchmarkChart):
    subdirectory = "sankey"

    def render(self, results: BenchmarkResults, output_dir: Path) -> None:
        frame = results.comparable_metric("disk_usage")
        flows = [build_storage_flow(language, frame[frame["language"] == language]) for language in languages_in(frame)]
        figure = go.Figure([SankeyView(flow).trace() for flow in flows])
        figure.data[0].visible = True  # the first language is shown when the page opens
        figure.update_layout(**self._layout(flows))
        save_interactive_html(figure, output_dir, "storage_sankey")

    def _layout(self, flows: list[StorageFlow]) -> dict:
        views = [SankeyView(flow) for flow in flows]
        return dict(
            title=views[0].title(), annotations=views[0].annotations(),
            updatemenus=[self._language_buttons(views)],
            font=dict(family=PLOTLY_FONT_FAMILY, size=13, color=INK),
            paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
            width=FIGURE_WIDTH, height=FIGURE_HEIGHT, margin=MARGIN,
            hoverlabel=dict(font=dict(family=PLOTLY_FONT_FAMILY, size=13)),
        )

    @staticmethod
    def _language_buttons(views: list["SankeyView"]) -> dict:
        buttons = [dict(label=f"  {language_label(view.flow.language)}  ", method="update",
                        args=[{"visible": [other is view for other in views]},
                              {"title": view.title(), "annotations": view.annotations()}])
                   for view in views]
        return dict(type="buttons", direction="right", buttons=buttons, showactive=True, active=0,
                    x=0.0, xanchor="left", y=1.12, yanchor="bottom", pad=dict(l=0, t=0),
                    bgcolor=SURFACE, bordercolor="#CBD5E0", font=dict(size=13, color=INK))


class SankeyView:
    """Trace, title and annotations for one language."""

    def __init__(self, flow: StorageFlow) -> None:
        self.flow = flow
        self.layout = NodeLayout(flow)

    def trace(self) -> go.Sankey:
        nodes, links = self.flow.nodes, self.flow.links
        return go.Sankey(
            visible=False, arrangement="fixed", valueformat=",.1f", valuesuffix=" MB",
            textfont=dict(color="rgba(0,0,0,0)", size=1),  # labels are drawn as annotations instead
            domain=dict(x=list(DOMAIN_X), y=[0, 1]),
            node=dict(label=[node.name for node in nodes], color=[node.color for node in nodes],
                      x=[COLUMN_X[node.layer] for node in nodes],
                      y=[self.layout.center_fraction(node) for node in nodes],
                      pad=NODE_PAD_PX, thickness=NODE_THICKNESS, line=dict(color=SURFACE, width=1),
                      customdata=[self._node_hover(node) for node in nodes],
                      hovertemplate="%{customdata}<extra></extra>"),
            link=dict(source=[link[0] for link in links], target=[link[1] for link in links],
                      value=[link[2] for link in links],
                      color=[rgba(nodes[link[1]].color, LINK_OPACITY) for link in links],
                      hovertemplate="%{source.label} → %{target.label}<br><b>%{value:,.1f} MB</b><extra></extra>"),
        )

    def title(self) -> dict:
        language = language_label(self.flow.language)
        subtitle = "Where the bytes go: raw books are written into three datalake layouts, then indexed three ways."
        return dict(text=f"<b>Storage footprint flow · {language}</b><br>"
                         f"<span style='font-size:14px;color:{INK_MUTED}'>{subtitle}</span>",
                    x=0.03, xanchor="left", y=0.975, yanchor="top", font=dict(size=22, color=INK))

    def annotations(self) -> list[dict]:
        labels = [self._node_annotation(node) for node in self.flow.nodes]
        headers = [self._column_header(layer) for layer in COLUMN_X]
        return [*labels, *headers, self._footnote()]

    def _node_annotation(self, node: StorageNode) -> dict:
        center_y = 1 - self.layout.center_fraction(node)
        if node.layer == "Raw":
            return _annotation(self._raw_text(), self.layout.paper_x(node) - 0.012, center_y, "right", "middle")
        if node.layer == "Index":
            return _annotation(self._index_text(node), self.layout.paper_x(node) + 0.014, center_y, "left", "middle")
        top_y = center_y + self.layout.height_fraction(node) / 2 + 0.008
        return _annotation(self._layout_text(node), self.layout.paper_x(node) - 0.006, top_y, "left", "bottom")

    def _raw_text(self) -> str:
        layout_count = sum(node.layer == "Datalake" for node in self.flow.nodes)
        written = self.flow.nodes[0].size_mb
        return f"<b>Raw corpus</b><br><span style='color:{INK_SECONDARY}'>{written:,.1f} MB written<br>" \
               f"into {layout_count} layouts</span>"

    @staticmethod
    def _layout_text(node: StorageNode) -> str:
        return f"<b>{node.name}</b>  <span style='color:{INK_SECONDARY}'>{node.size_mb:,.1f} MB · " \
               f"{_file_count_text(node.file_count)}</span>"

    def _index_text(self, node: StorageNode) -> str:
        share = node.size_mb / self.flow.total_index_mb
        files = _file_count_text(node.file_count) if node.file_count else "database collection"
        return f"<b>{node.name}</b><br><span style='color:{INK_SECONDARY}'>{node.size_mb:,.1f} MB · {share:.0%} of " \
               f"index storage<br>{files}</span>"

    def _column_header(self, layer: str) -> dict:
        header_x = DOMAIN_X[0] + COLUMN_X[layer] * (DOMAIN_X[1] - DOMAIN_X[0])
        anchor = {"Raw": "right", "Datalake": "center", "Index": "left"}[layer]
        offset = {"Raw": 0.012, "Datalake": 0.0, "Index": -0.004}[layer]
        header = _annotation(f"<b>{COLUMN_HEADERS[layer]}</b>", header_x + offset, 1.06, anchor, "bottom")
        header["font"] = dict(size=12, color=INK_MUTED)
        return header

    @staticmethod
    def _footnote() -> dict:
        footnote = _annotation(FOOTNOTE, 0.0, -0.07, "left", "top")
        footnote["font"] = dict(size=11.5, color=INK_MUTED)
        return footnote

    @staticmethod
    def _node_hover(node: StorageNode) -> str:
        files = f"<br>{_file_count_text(node.file_count)}" if node.file_count else ""
        return f"<b>{node.layer} · {node.name}</b><br>{node.size_mb:,.1f} MB on disk{files}"


def _annotation(text: str, x: float, y: float, x_anchor: str, y_anchor: str) -> dict:
    return dict(text=text, x=x, y=y, xref="paper", yref="paper", xanchor=x_anchor, yanchor=y_anchor,
                showarrow=False, align="left" if x_anchor != "right" else "right",
                font=dict(size=13, color=INK), bgcolor="rgba(255,255,255,0.85)", borderpad=3)


def _file_count_text(file_count: int) -> str:
    return "1 file" if file_count == 1 else f"{file_count:,} files"
