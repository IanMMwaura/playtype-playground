from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.routing import Route

from shiny import App, reactive, render, ui
from shiny.render.renderer import Renderer

from shared import DATA_SOURCE, PLAY_TYPES, app_dir, playtype_data


COLORS = {
    "player": "#8B9EAC",
    "primary": "#007A33",
    "compare": "#8CA099",
    "muted": "#8795A2",
    "grid": "rgba(151, 166, 183, 0.14)",
    "paper": "rgba(0,0,0,0)",
    "text": "#E3E8EC",
}

COMPARISON_COLORS = ("#007A33", "#8CA099", "#A8B4BF", "#718A78")
TEAM_COLORS = {
    "ATL": "#E03A3E", "BOS": "#007A33", "BKN": "#000000", "NJN": "#000000",
    "CHA": "#1D1160", "CHH": "#1D1160", "CHI": "#CE1141", "CLE": "#860038",
    "DAL": "#00538C", "DEN": "#0E2240", "DET": "#C8102E", "GSW": "#1D428A",
    "HOU": "#CE1141", "IND": "#002D62", "LAC": "#C8102E", "LAL": "#552583",
    "MEM": "#5D76A9", "VAN": "#5D76A9", "MIA": "#98002E", "MIL": "#00471B",
    "MIN": "#0C2340", "NOP": "#0C2340", "NOH": "#0C2340", "NYK": "#F58426",
    "OKC": "#007AC1", "SEA": "#007AC1", "ORL": "#0077C0", "PHI": "#006BB6",
    "PHX": "#1D1160", "POR": "#E03A3E", "SAC": "#5A2D81", "SAS": "#C4CED4",
    "TOR": "#CE1141", "UTA": "#002B5C", "WAS": "#002B5C",
}
TEAM_COLOR_PALETTES = {
    "ATL": ("#E03A3E", "#C1D32F", "#FDB927", "#26282A"),
    "BOS": ("#007A33", "#BA9653", "#963821", "#000000"),
    "BKN": ("#000000", "#707271", "#A7A9AC", "#FFFFFF"),
    "CHA": ("#1D1160", "#00788C", "#A1A1A4", "#280071"),
    "CHI": ("#CE1141", "#000000", "#FFFFFF", "#8A8D8F"),
    "CLE": ("#860038", "#FDBB30", "#041E42", "#FFFFFF"),
    "DAL": ("#00538C", "#B8C4CA", "#002B5E", "#000000"),
    "DEN": ("#0E2240", "#FEC524", "#8B2131", "#1D428A"),
    "DET": ("#C8102E", "#1D42BA", "#BEC0C2", "#002D62"),
    "GSW": ("#1D428A", "#FFC72C", "#C8102E", "#FFFFFF"),
    "HOU": ("#CE1141", "#000000", "#C4CED4", "#FFFFFF"),
    "IND": ("#002D62", "#FDBB30", "#BEC0C2", "#FFFFFF"),
    "LAC": ("#C8102E", "#1D428A", "#BEC0C2", "#000000"),
    "LAL": ("#552583", "#FDB927", "#000000", "#FFFFFF"),
    "MEM": ("#5D76A9", "#12173F", "#F5B112", "#707271"),
    "MIA": ("#98002E", "#F9A01B", "#000000", "#FFFFFF"),
    "MIL": ("#00471B", "#EEE1C6", "#0077C0", "#000000"),
    "MIN": ("#0C2340", "#236192", "#9EA2A2", "#78BE20"),
    "NOP": ("#0C2340", "#C8102E", "#85714D", "#FFFFFF"),
    "NYK": ("#F58426", "#006BB6", "#BEC0C2", "#000000"),
    "OKC": ("#007AC1", "#EF3B24", "#FDBB30", "#002D62"),
    "ORL": ("#0077C0", "#C4CED4", "#000000", "#FFFFFF"),
    "PHI": ("#006BB6", "#ED174C", "#002B5C", "#FFFFFF"),
    "PHX": ("#1D1160", "#E56020", "#F9AD1B", "#000000"),
    "POR": ("#E03A3E", "#000000", "#FFFFFF", "#A7A9AC"),
    "SAC": ("#5A2D81", "#63727A", "#000000", "#FFFFFF"),
    "SAS": ("#C4CED4", "#000000", "#FFFFFF", "#8A8D8F"),
    "TOR": ("#CE1141", "#000000", "#A1A1A4", "#B4975A"),
    "UTA": ("#002B5C", "#F9A01B", "#00471B", "#FFFFFF"),
    "WAS": ("#002B5C", "#E31837", "#C4CED4", "#FFFFFF"),
}
TEAM_COLOR_PALETTES.update({
    "NJN": TEAM_COLOR_PALETTES["BKN"],
    "CHH": TEAM_COLOR_PALETTES["CHA"],
    "VAN": TEAM_COLOR_PALETTES["MEM"],
    "NOH": TEAM_COLOR_PALETTES["NOP"],
    "SEA": TEAM_COLOR_PALETTES["OKC"],
})
REMOTE_HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
REMOTE_SEASON_HEADSHOT_URL = (
    "https://cdn.nba.com/headshots/nba/{team_id}/{season_year}/260x190/{player_id}.png"
)
HEADSHOT_URL = "/headshots/latest/{player_id}.png"
SEASON_HEADSHOT_URL = "/headshots/{team_id}/{season_year}/{player_id}.png"
TEAM_LOGO_URL = "https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"
TEAM_IDS = {
    "ATL": 1610612737, "BOS": 1610612738, "CLE": 1610612739,
    "NOP": 1610612740, "NOH": 1610612740, "CHI": 1610612741,
    "DAL": 1610612742, "DEN": 1610612743, "GSW": 1610612744,
    "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747,
    "MIA": 1610612748, "MIL": 1610612749, "MIN": 1610612750,
    "BKN": 1610612751, "NJN": 1610612751, "NYK": 1610612752,
    "ORL": 1610612753, "IND": 1610612754, "PHI": 1610612755,
    "PHX": 1610612756, "POR": 1610612757, "SAC": 1610612758,
    "SAS": 1610612759, "OKC": 1610612760, "SEA": 1610612760,
    "TOR": 1610612761, "UTA": 1610612762, "MEM": 1610612763,
    "VAN": 1610612763, "WAS": 1610612764, "DET": 1610612765,
    "CHA": 1610612766, "CHH": 1610612766,
}
COMPARISON_STATS = (
    ("ppp", "PPP"),
    ("frequency", "Frequency"),
    ("possessions", "Possessions"),
    ("efg_pct", "Effective FG%"),
    ("score_pct", "Score rate"),
    ("tov_pct", "Turnover rate"),
    ("percentile", "Percentile"),
)

CANONICAL_URL = os.getenv("PLAYTYPE_PLAYGROUND_CANONICAL_URL", "http://127.0.0.1:8000/")
if not CANONICAL_URL.endswith("/"):
    CANONICAL_URL += "/"
BODY_CONTROLS = os.getenv("PLAYTYPE_PLAYGROUND_BODY_CONTROLS", "1") != "0"

APP_DESCRIPTION = (
    "Explore NBA playtype volume and efficiency by player, team, and season."
)

STRUCTURED_DATA = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "Playtype Playground",
    "applicationCategory": "SportsApplication",
    "operatingSystem": "Web",
    "description": APP_DESCRIPTION,
    "url": CANONICAL_URL,
}

METRICS = {
    "frequency": {"label": "Play frequency", "tick": ".0%", "hover": ".1%"},
    "possessions": {"label": "Possessions", "tick": ",d", "hover": ",d"},
    "ppp": {"label": "Points per possession", "tick": ".2f", "hover": ".3f"},
    "efg_pct": {"label": "Effective FG%", "tick": ".0f", "hover": ".1f", "suffix": "%"},
    "score_pct": {"label": "Score rate", "tick": ".0f", "hover": ".1f", "suffix": "%"},
    "tov_pct": {"label": "Turnover rate", "tick": ".0f", "hover": ".1f", "suffix": "%"},
}

METRIC_DEFINITIONS = {
    "ppp": "Points scored per possession used in the selected play type.",
    "frequency": "Share of a player's offensive possessions used in this play type.",
    "possessions": "Number of qualifying possessions in the selected sample.",
    "percentile": "Efficiency rank relative to qualified NBA players, from 0 to 100.",
    "efg_pct": "Field-goal percentage adjusted to give extra weight to made three-pointers.",
    "score_pct": "Share of possessions that produced points.",
    "tov_pct": "Share of possessions that ended in a turnover; lower is generally better.",
}


class render_plotly_json(Renderer[dict[str, object]]):
    """Pass Plotly JSON to the app's Shiny output binding."""

    async def transform(self, value: dict[str, object]) -> dict[str, object]:
        return value


def plot_output(output_id: str, *, height: int, label: str):
    return ui.tags.div(
        id=output_id,
        class_="playtype-plot-output",
        role="img",
        aria_label=label,
        style=f"height:{height}px;width:100%;",
    )


def plot_payload(
    figure: go.Figure,
    *,
    label: str,
    click_input: str | None = None,
) -> dict[str, object]:
    payload = json.loads(figure.to_json())
    return {
        "data": payload["data"],
        "layout": payload["layout"],
        "config": {
            "responsive": True,
            "displaylogo": False,
            "scrollZoom": False,
            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
        },
        "clickInput": click_input,
        "label": label,
    }

SEASONS = sorted(playtype_data["season"].astype(str).unique(), reverse=True)
PLAYER_CHOICES = sorted(playtype_data["player"].unique())
INITIAL_PLAYER_CHOICES = sorted(
    playtype_data.loc[
        playtype_data["season"].astype(str) == SEASONS[0], "player"
    ]
    .astype(str)
    .unique()
)
PLAYER_SEARCH_CHOICES = {
    "": "",
    **{player: player for player in INITIAL_PLAYER_CHOICES},
}
TEAM_CHOICES = ["All teams", *sorted({str(team).split("/")[0] for team in playtype_data["team"]})]
DEFAULT_PLAY_TYPE = "Isolation"
DEFAULT_POOL = playtype_data[
    (playtype_data["season"].astype(str) == SEASONS[0])
    & (playtype_data["play_type"] == DEFAULT_PLAY_TYPE)
].sort_values("possessions", ascending=False)
INITIAL_MAX_POSSESSIONS = int(DEFAULT_POOL["possessions"].max())


DEFAULT_COMPARISON_PLAYERS: list[str] = []


def initials(name: str) -> str:
    parts = [part for part in name.replace(".", "").split() if part]
    return "".join(part[0] for part in parts[:2]).upper()


def team_id_for(team: object) -> int | None:
    return TEAM_IDS.get(str(team).split("/")[0])


def team_color_for(team: object, fallback: str = COLORS["primary"]) -> str:
    return TEAM_COLORS.get(str(team).split("/")[0], fallback)


def player_team_color(frame: pd.DataFrame, player: str, fallback: str) -> str:
    rows = frame[frame["player"] == player]
    if rows.empty:
        return fallback
    identity = rows.sort_values("possessions", ascending=False).iloc[0]
    return team_color_for(identity["team"], fallback)


def comparison_series_colors(frame: pd.DataFrame, players: list[str]) -> dict[str, str]:
    team_counts: dict[str, int] = {}
    colors: dict[str, str] = {}
    for index, player in enumerate(players):
        rows = frame[frame["player"] == player]
        if rows.empty:
            colors[player] = COMPARISON_COLORS[index % len(COMPARISON_COLORS)]
            continue
        identity = rows.sort_values("possessions", ascending=False).iloc[0]
        team = str(identity["team"]).split("/")[0]
        palette = TEAM_COLOR_PALETTES.get(team, (team_color_for(team),))
        palette_index = team_counts.get(team, 0)
        colors[player] = palette[palette_index % len(palette)]
        team_counts[team] = palette_index + 1
    return colors


def color_with_alpha(color: str, alpha: float) -> str:
    value = color.lstrip("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def headshot_url(player_id: object, season: object | None = None, team: object | None = None) -> str:
    team_id = team_id_for(team) if team is not None else None
    if season is not None and team_id is not None:
        return SEASON_HEADSHOT_URL.format(
            team_id=team_id,
            season_year=str(season).split("-")[0],
            player_id=int(player_id),
        )
    return HEADSHOT_URL.format(player_id=int(player_id))


def headshot_tag(
    player_id: object,
    player: str,
    *,
    class_name: str,
    season: object | None = None,
    team: object | None = None,
):
    """Show a headshot, or the player's initials if the image is unavailable."""

    return ui.div(
        ui.tags.img(
            src=headshot_url(player_id, season, team),
            alt=f"{player} headshot",
            loading="lazy",
            onerror=(
                f"if(!this.dataset.fallback){{this.dataset.fallback='1';"
                f"this.src='{headshot_url(player_id)}';}}else{{"
                "this.style.display='none';this.nextElementSibling.style.display='grid';}"
            ),
        ),
        ui.tags.span(initials(player), class_="headshot-fallback"),
        class_=class_name,
    )


def team_logo_tag(team: object):
    abbreviation = str(team).split("/")[0]
    team_id = TEAM_IDS.get(abbreviation)
    if team_id is None:
        return None
    return ui.tags.img(
        src=TEAM_LOGO_URL.format(team_id=team_id),
        alt=f"{abbreviation} logo",
        class_="team-logo",
    )


def format_comparison_value(key: str, value: float) -> str:
    if key == "frequency":
        return f"{value:.1%}"
    if key == "possessions":
        return f"{int(value):,}"
    if key in {"efg_pct", "score_pct", "tov_pct"}:
        return f"{value:.1f}%"
    if key == "percentile":
        return ordinal(int(value))
    return f"{value:.3f}"


def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def weighted_average(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return 0.0
    weights = frame["possessions"].clip(lower=1)
    return float(np.average(frame[column], weights=weights))


def sortable_header(label: str, column: int, *, title: str = ""):
    return ui.tags.button(
        label,
        type="button",
        class_="table-sort-button",
        data_sort_column=str(column),
        title=title or f"Sort by {label}",
        aria_label=f"Sort by {label}",
    )


brand = ui.div(
    ui.div(
        ui.HTML(
            '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">'
            '<circle cx="32" cy="32" r="19" fill="#071018"/>'
            '<g fill="none" stroke="#007a33" stroke-width="3" stroke-linecap="round">'
            '<path d="M13 32h38"/>'
            '<path d="M32 13c-10 9-10 29 0 38"/>'
            '<path d="M32 13c10 9 10 29 0 38"/>'
            '</g></svg>'
        ),
        class_="brand-mark",
    ),
    ui.div(
        ui.tags.span("PLAYTYPE PLAYGROUND", class_="brand-name"),
        ui.tags.span("NBA ANALYTICS", class_="brand-kicker"),
        class_="brand-copy",
    ),
    ui.div(ui.input_dark_mode(id="color_mode", mode="dark"), class_="theme-control"),
    class_="brand",
)

page_metadata = ui.head_content(
    ui.tags.meta(name="description", content=APP_DESCRIPTION),
    ui.tags.meta(name="robots", content="index, follow"),
    ui.tags.meta(property="og:type", content="website"),
    ui.tags.meta(property="og:site_name", content="Playtype Playground"),
    ui.tags.meta(property="og:title", content="Playtype Playground | NBA Analytics"),
    ui.tags.meta(property="og:description", content=APP_DESCRIPTION),
    ui.tags.meta(property="og:url", content=CANONICAL_URL),
    ui.tags.meta(property="og:image", content=f"{CANONICAL_URL}social-preview.svg"),
    ui.tags.meta(name="twitter:card", content="summary_large_image"),
    ui.tags.meta(name="twitter:title", content="Playtype Playground | NBA Analytics"),
    ui.tags.meta(name="twitter:description", content=APP_DESCRIPTION),
    ui.tags.meta(name="twitter:image", content=f"{CANONICAL_URL}social-preview.svg"),
    ui.tags.link(rel="canonical", href=CANONICAL_URL),
    ui.tags.link(rel="icon", type="image/svg+xml", href="/favicon.svg?v=20260901-4"),
    ui.tags.script(src="https://cdn.plot.ly/plotly-3.3.1.min.js", defer=""),
    ui.tags.script(
        src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js",
        defer="",
    ),
    ui.tags.script(src="/charts.js?v=20260831-2", defer=""),
    *(
        [ui.tags.script(src="/body-layout.js?v=20260901-2", defer="")]
        if BODY_CONTROLS
        else []
    ),
    ui.tags.script(
        ui.HTML(
            "document.addEventListener('change',function(event){"
            "if(event.target.id!=='season'||!event.isTrusted)return;"
            "['highlight','compare_players'].forEach(function(id){"
            "var input=document.getElementById(id);"
            "if(input&&input.selectize)input.selectize.clear();"
            "});"
            "});"
        )
    ),
    ui.tags.script(ui.HTML(json.dumps(STRUCTURED_DATA)), type="application/ld+json"),
)

sidebar = ui.sidebar(
    ui.input_select("season", "Season", SEASONS, selected=SEASONS[0]),
    ui.input_select("play_type", "Play type", list(PLAY_TYPES), selected=DEFAULT_PLAY_TYPE),
    ui.input_selectize(
        "team_filter",
        "Team",
        TEAM_CHOICES,
        selected="All teams",
        options={"placeholder": "Search teams..."},
    ),
    ui.input_checkbox_group(
        "position",
        "Role / position",
        {"G": "Guard", "F": "Forward", "C": "Center"},
        selected=["G", "F", "C"],
        inline=True,
    ),
    ui.input_select(
        "usage_tier",
        "Usage tier",
        {
            "all": "All usage levels",
            "high": "High frequency (20%+)",
            "medium": "Regular frequency (10-20%)",
            "low": "Situational frequency (under 10%)",
        },
        selected="all",
    ),
    ui.input_slider(
        "min_possessions",
        "Minimum possessions",
        min=0,
        max=INITIAL_MAX_POSSESSIONS,
        value=35,
        step=5,
    ),
    ui.div(class_="sidebar-rule"),
    ui.tags.span("PLAYER SEARCH", class_="eyebrow section-eyebrow"),
    ui.input_selectize(
        "highlight",
        "Search player",
        PLAYER_SEARCH_CHOICES,
        selected="",
        options={
            "placeholder": "Type a player name...",
            "maxOptions": len(PLAYER_CHOICES),
            "openOnFocus": True,
        },
    ),
    ui.input_selectize(
        "compare_players",
        "Compare players (up to 4)",
        INITIAL_PLAYER_CHOICES,
        selected=[],
        multiple=True,
        remove_button=True,
        options={
            "placeholder": "Search and add players...",
            "maxItems": 4,
            "maxOptions": len(PLAYER_CHOICES),
        },
    ),
    ui.div(class_="sidebar-rule"),
    ui.tags.span("CHART SETTINGS", class_="eyebrow section-eyebrow"),
    ui.input_select(
        "x_metric",
        "Horizontal axis",
        {"frequency": "Play frequency", "possessions": "Possessions"},
        selected="frequency",
    ),
    ui.input_select(
        "y_metric",
        "Vertical axis",
        {
            "ppp": "Points per possession",
            "efg_pct": "Effective FG%",
            "score_pct": "Score rate",
            "tov_pct": "Turnover rate",
        },
        selected="ppp",
    ),
    ui.input_switch("avg_overlay", "League-average crosshair", value=True),
    ui.input_switch("headshots", "Use player headshots", value=True),
    ui.input_select(
        "label_mode",
        "Player labels",
        {
            "highlight": "Pinned player only",
            "all": "All players",
            "none": "No labels",
        },
        selected="highlight",
    ),
    ui.tags.details(
        ui.tags.summary("Metric definitions"),
        *[
            ui.tags.p(ui.tags.strong(f"{key.upper()}: "), definition)
            for key, definition in METRIC_DEFINITIONS.items()
        ],
        class_="metric-glossary",
    ),
    ui.input_action_button("reset", "Reset dashboard", class_="reset-button"),
    ui.div(
        ui.tags.span("DATA", class_="source-label"),
        ui.tags.span(DATA_SOURCE.upper(), class_="source-value"),
        class_="source-chip sidebar-source",
    ),
    width=304,
    open="desktop",
)


app_ui = ui.page_sidebar(
    sidebar,
    page_metadata,
    ui.div(
        ui.div(
            ui.output_ui("context_title"),
            class_="context-copy",
        ),
        ui.div(
            ui.tags.button("Share view", id="share_view", type="button", class_="utility-button"),
            ui.download_button("download_csv", "Download CSV", class_="utility-button"),
            class_="context-actions",
        ),
        class_="context-strip",
    ),
    ui.div(
        ui.div(
            ui.tags.span("Players in view", class_="metric-label"),
            ui.output_ui("players_kpi"),
            class_="metric-item",
        ),
        ui.div(
            ui.tags.span("Total possessions", class_="metric-label"),
            ui.output_ui("possessions_kpi"),
            class_="metric-item",
        ),
        class_="metric-strip",
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.span("VOLUME AND EFFICIENCY", class_="eyebrow"),
                    ui.tags.h2("Player landscape"),
                    class_="card-heading",
                ),
                ui.output_ui("landscape_legend"),
                class_="split-header",
            ),
            plot_output(
                "scatterplot",
                height=500,
                label="Player volume and efficiency scatter plot",
            ),
            ui.card_footer(
                ui.tags.span("SELECT A PLAYER", class_="interaction-label"),
                "Hover for details. Click a point to pin that player.",
                ui.tags.button(
                    "Save PNG",
                    id="download_scatter_png",
                    type="button",
                    class_="chart-download-button",
                ),
                class_="interaction-note",
            ),
            full_screen=True,
            class_="dashboard-card hero-card",
        ),
        ui.card(
            ui.card_header(
                ui.output_ui("player_heading"),
                ui.tags.button(
                    "Save PNG",
                    type="button",
                    class_="card-export-button",
                    data_export_target=".player-card",
                    data_export_name="playtype-playground-pinned-player",
                ),
                class_="player-card-header",
            ),
            ui.output_ui("player_snapshot"),
            class_="dashboard-card player-card",
        ),
        col_widths=[8, 4],
        fill=False,
        class_="main-grid",
    ),
    ui.tags.section(
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.span("PLAYER OVERVIEW", class_="eyebrow"),
                    ui.output_ui("overview_heading"),
                    class_="card-heading",
                ),
                ui.tags.button(
                    "Save PNG",
                    type="button",
                    class_="card-export-button",
                    data_export_target=".overview-card",
                    data_export_name="playtype-playground-player-overview",
                ),
                class_="split-header",
            ),
            ui.output_ui("player_insights"),
            ui.layout_columns(
                ui.output_ui("overview_table"),
                plot_output(
                    "overview_radar",
                    height=390,
                    label="Pinned player playtype percentile radar chart",
                ),
                col_widths=[7, 5],
                fill=False,
                class_="overview-grid",
            ),
            class_="dashboard-card overview-card",
        ),
        id="player-overview",
    ),
    ui.card(
        ui.card_header(
            ui.div(
                ui.tags.span("SEASON HISTORY", class_="eyebrow"),
                ui.output_ui("trend_heading"),
                class_="card-heading",
            ),
            ui.input_select(
                "trend_metric",
                "Trend metric",
                {
                    "ppp": "Points per possession",
                    "frequency": "Play frequency",
                    "possessions": "Possessions",
                    "percentile": "Efficiency percentile",
                },
                selected="ppp",
            ),
            ui.tags.button(
                "Save PNG",
                type="button",
                class_="card-export-button",
                data_export_target=".trend-card",
                data_export_name="playtype-playground-season-history",
            ),
            class_="split-header trend-header",
        ),
        plot_output(
            "season_trend",
            height=310,
            label="Selected player history by season",
        ),
        class_="dashboard-card trend-card",
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.span("COMPARISON", class_="eyebrow"),
                    ui.tags.h2("Player comparison"),
                    ui.output_ui("comparison_context"),
                    class_="card-heading",
                ),
                ui.output_ui("comparison_legend"),
                class_="split-header",
            ),
            ui.output_ui("comparison_matrix"),
            plot_output(
                "profile_plot",
                height=380,
                label="Up to four players compared across playtype efficiency",
            ),
            ui.card_footer(
                "Click a stat name to order players by that measure.",
                ui.tags.button(
                    "Save PNG",
                    id="download_comparison_png",
                    type="button",
                    class_="chart-download-button card-export-button",
                    data_export_target=".comparison-card",
                    data_export_name="playtype-playground-player-comparison",
                ),
                class_="table-note comparison-footer",
            ),
            class_="dashboard-card profile-card comparison-card",
        ),
        ui.card(
            ui.card_header(
                ui.div(
                    ui.tags.span("PPP LEADERS", class_="eyebrow"),
                    ui.tags.h2("Top 15 players"),
                    ui.output_ui("leaderboard_metric"),
                    class_="card-heading",
                )
            ),
            ui.output_ui("leaderboard"),
            ui.card_footer(
                "Ranked by PPP for the current filters",
                ui.tags.button(
                    "Save PNG",
                    type="button",
                    class_="card-export-button",
                    data_export_target=".leaderboard-card",
                    data_export_name="playtype-playground-efficiency-board",
                ),
                class_="table-note export-footer",
            ),
            class_="dashboard-card leaderboard-card",
        ),
        col_widths=[8, 4],
        fill=False,
        class_="lower-grid",
    ),
    ui.div(
        ui.tags.span("PLAYTYPE PLAYGROUND / NBA ANALYTICS"),
        ui.div(
            ui.tags.a("Privacy", href="/privacy.html"),
            ui.tags.a("Terms", href="/terms.html"),
            ui.tags.span("Python / Shiny / Plotly"),
            class_="footer-links",
        ),
        class_="app-footer",
    ),
    ui.div("Loading dashboard...", id="app_status", role="status", aria_live="polite"),
    ui.div(ui.input_text("comparison_sort", None, value=""), class_="hidden-input"),
    ui.include_css(app_dir / "styles.css"),
    title=brand,
    window_title="Playtype Playground | NBA Analytics",
    fillable=False,
    lang="en",
)


def server(input, output, session):
    selected_player = reactive.Value(None)

    @reactive.calc
    def available_player_names() -> list[str]:
        frame = playtype_data[
            playtype_data["season"].astype(str) == str(input.season())
        ]
        return sorted(frame["player"].astype(str).unique())

    @reactive.calc
    def filtered_data() -> pd.DataFrame:
        positions = list(input.position() or [])
        frame = playtype_data[
            (playtype_data["season"].astype(str) == str(input.season()))
            & (playtype_data["play_type"] == input.play_type())
            & (playtype_data["position"].isin(positions))
            & (playtype_data["possessions"] >= input.min_possessions())
        ].copy()
        team = str(input.team_filter() or "All teams")
        if team != "All teams":
            frame = frame[frame["team"].astype(str).str.split("/").apply(lambda teams: team in teams)]
        usage_tier = str(input.usage_tier() or "all")
        if usage_tier == "high":
            frame = frame[frame["frequency"] >= 0.20]
        elif usage_tier == "medium":
            frame = frame[(frame["frequency"] >= 0.10) & (frame["frequency"] < 0.20)]
        elif usage_tier == "low":
            frame = frame[frame["frequency"] < 0.10]
        return frame.sort_values("ppp", ascending=False, ignore_index=True)

    @reactive.calc
    def selected_row() -> pd.Series | None:
        frame = playtype_data[
            (playtype_data["season"].astype(str) == str(input.season()))
            & (playtype_data["play_type"] == input.play_type())
            & (playtype_data["player"] == selected_player.get())
        ]
        return None if frame.empty else frame.iloc[0]

    @reactive.calc
    def selected_profile() -> pd.DataFrame:
        player = selected_player.get()
        if not player:
            return playtype_data.iloc[0:0].copy()
        frame = playtype_data[
            (playtype_data["season"].astype(str) == str(input.season()))
            & (playtype_data["player"] == player)
        ].copy()
        order = {play_type: index for index, play_type in enumerate(PLAY_TYPES)}
        frame["playtype_order"] = frame["play_type"].map(order)
        return frame.sort_values("playtype_order", ignore_index=True)

    @reactive.calc
    def comparison_names() -> list[str]:
        raw = input.compare_players() or []
        if isinstance(raw, str):
            raw = [raw]
        names: list[str] = []
        available = set(available_player_names())
        for name in raw:
            value = str(name)
            if value in available and value not in names:
                names.append(value)
        names = names[:4]
        sort_key = str(input.comparison_sort() or "")
        if sort_key in {key for key, _ in COMPARISON_STATS} and len(names) > 1:
            current = playtype_data[
                (playtype_data["season"].astype(str) == str(input.season()))
                & (playtype_data["play_type"] == input.play_type())
            ].set_index("player")
            names.sort(
                key=lambda name: float(current.at[name, sort_key]) if name in current.index else float("-inf"),
                reverse=sort_key != "tov_pct",
            )
        return names

    @reactive.effect
    @reactive.event(input.season, input.play_type)
    def _sync_possession_ceiling():
        frame = playtype_data[
            (playtype_data["season"].astype(str) == str(input.season()))
            & (playtype_data["play_type"] == input.play_type())
        ]
        maximum = max(1, int(frame["possessions"].max())) if not frame.empty else 1
        current = min(int(input.min_possessions()), maximum)
        ui.update_slider(
            "min_possessions",
            max=maximum,
            value=current,
            session=session,
        )

    @reactive.effect
    @reactive.event(input.season)
    def _sync_player_choices():
        names = available_player_names()
        available = set(names)
        highlighted = str(input.highlight() or "").strip()
        highlighted = highlighted if highlighted in available else ""
        raw_comparisons = input.compare_players() or []
        if isinstance(raw_comparisons, str):
            raw_comparisons = [raw_comparisons]
        comparisons = [
            str(name) for name in raw_comparisons if str(name) in available
        ][:4]
        ui.update_selectize(
            "highlight",
            choices={"": "", **{name: name for name in names}},
            selected=highlighted,
            session=session,
        )
        ui.update_selectize(
            "compare_players",
            choices=names,
            selected=comparisons,
            session=session,
        )
        if not highlighted:
            selected_player.set(None)

    @reactive.effect
    def _sync_selected_player():
        player = str(input.highlight() or "").strip()
        selected_player.set(player if player in set(available_player_names()) else None)

    @reactive.effect
    @reactive.event(input.scatter_point)
    def _sync_chart_selection():
        if input.scatter_point():
            player = str(input.scatter_point())
            selected_player.set(player)
            ui.update_selectize("highlight", selected=player, session=session)

    @reactive.effect
    @reactive.event(input.reset)
    def _reset_dashboard():
        ui.update_select("season", selected=SEASONS[0])
        ui.update_select("play_type", selected=DEFAULT_PLAY_TYPE)
        ui.update_selectize("team_filter", selected="All teams")
        ui.update_checkbox_group("position", selected=["G", "F", "C"])
        ui.update_select("usage_tier", selected="all")
        ui.update_slider("min_possessions", value=35)
        ui.update_select("x_metric", selected="frequency")
        ui.update_select("y_metric", selected="ppp")
        ui.update_switch("avg_overlay", value=True)
        ui.update_switch("headshots", value=True)
        ui.update_select("label_mode", selected="highlight")
        ui.update_select("trend_metric", selected="ppp")
        ui.update_text("comparison_sort", value="")
        ui.update_selectize("highlight", selected="")
        ui.update_selectize(
            "compare_players",
            selected=DEFAULT_COMPARISON_PLAYERS,
        )
        selected_player.set(None)

    @render.ui
    def context_title():
        return ui.tags.h1(
            input.play_type(),
            ui.tags.span(f" / {input.season()}", class_="context-season"),
        )

    @render.ui
    def players_kpi():
        frame = filtered_data()
        return ui.tags.span(f"{len(frame)}", class_="kpi-value")

    @render.ui
    def possessions_kpi():
        total = int(filtered_data()["possessions"].sum())
        return ui.tags.span(f"{total:,}", class_="kpi-value")

    @render.download(filename="playtype-playground-filtered.csv")
    def download_csv():
        export_columns = [
            "season", "player", "team", "position", "play_type", "possessions",
            "frequency", "ppp", "percentile", "efg_pct", "score_pct", "tov_pct",
        ]
        yield filtered_data()[export_columns].to_csv(index=False)

    @render.ui
    def landscape_legend():
        if input.headshots():
            return None
        return ui.div(
            ui.tags.span(class_="legend-mark guard"),
            "Guards",
            ui.tags.span(class_="legend-mark forward"),
            "Forwards",
            ui.tags.span(class_="legend-mark center"),
            "Centers",
            class_="position-legend",
        )

    @render_plotly_json
    def scatterplot():
        frame = filtered_data()
        x_col = input.x_metric()
        y_col = input.y_metric()
        light_mode = input.color_mode() == "light"
        grid_color = "rgba(44,70,55,.12)" if light_mode else COLORS["grid"]

        if frame.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No players clear this filter set.<br><span style='font-size:12px'>Lower the possession threshold or add a position.</span>",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font={"color": COLORS["text"], "size": 16},
            )
            fig.update_layout(**_chart_layout(height=500, light_mode=light_mode))
            return plot_payload(
                fig,
                label="No players match the active scatter plot filters",
                click_input="scatter_point",
            )

        custom_columns = [
            "player",
            "team",
            "position",
            "possessions",
            "frequency",
            "ppp",
            "efg_pct",
            "tov_pct",
            "percentile",
        ]
        fig = px.scatter(
            frame,
            x=x_col,
            y=y_col,
            size="possessions",
            symbol="position",
            symbol_map={"G": "circle", "F": "square", "C": "diamond"},
            color_discrete_sequence=[COLORS["player"]],
            category_orders={"position": ["G", "F", "C"]},
            custom_data=custom_columns,
            size_max=30,
        )
        fig.update_traces(
            marker={"opacity": 0.78, "line": {"color": "rgba(255,255,255,.34)", "width": 1}},
            hovertemplate=(
                "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                "<span style='color:#93A4B7'>%{customdata[2]} · %{customdata[3]:,} possessions</span><br><br>"
                "Frequency&nbsp;&nbsp;<b>%{customdata[4]:.1%}</b><br>"
                "PPP&nbsp;&nbsp;<b>%{customdata[5]:.3f}</b><br>"
                "eFG%&nbsp;&nbsp;<b>%{customdata[6]:.1f}%</b><br>"
                "TOV%&nbsp;&nbsp;<b>%{customdata[7]:.1f}%</b><br>"
                "Percentile&nbsp;&nbsp;<b>%{customdata[8]}</b><extra></extra>"
            ),
        )
        label_mode = str(input.label_mode() or "highlight")
        if label_mode == "all":
            for trace in fig.data:
                trace.mode = "markers+text"
                trace.text = [str(item[0]) for item in trace.customdata]
                trace.textposition = "top center"
                trace.textfont = {"size": 8, "color": "#53665A" if light_mode else "#9BAAB8"}

        if input.headshots():
            fig.update_traces(
                marker={
                    "opacity": 0.025,
                    "line": {"color": "rgba(255,255,255,.08)", "width": 1},
                }
            )
            x_span = max(float(frame[x_col].max() - frame[x_col].min()), 0.001)
            y_span = max(float(frame[y_col].max() - frame[y_col].min()), 0.001)
            max_possessions = max(float(frame["possessions"].max()), 1)
            for row in frame.itertuples(index=False):
                size_scale = 0.05 + 0.035 * np.sqrt(row.possessions / max_possessions)
                fig.add_layout_image(
                    source=headshot_url(row.player_id, input.season(), row.team),
                    x=getattr(row, x_col),
                    y=getattr(row, y_col),
                    xref="x",
                    yref="y",
                    sizex=x_span * size_scale * 1.35,
                    sizey=y_span * size_scale,
                    xanchor="center",
                    yanchor="middle",
                    sizing="contain",
                    opacity=0.9,
                    layer="above",
                )

        if input.avg_overlay():
            avg_x = weighted_average(frame, x_col)
            avg_y = weighted_average(frame, y_col)
            average_line = "rgba(58,82,68,.58)" if light_mode else "rgba(211,221,231,.55)"
            fig.add_vline(x=avg_x, line_width=1, line_dash="dot", line_color=average_line)
            fig.add_hline(y=avg_y, line_width=1, line_dash="dot", line_color=average_line)
            fig.add_annotation(
                x=avg_x,
                y=1.015,
                xref="x",
                yref="paper",
                text="AVG",
                showarrow=False,
                font={"size": 9, "color": "#53665A" if light_mode else COLORS["muted"]},
                bgcolor="#EEF1ED" if light_mode else "#0D1925",
                borderpad=3,
            )

        selected_name = selected_player.get()
        focus_players = [(selected_name, COLORS["primary"], "circle")] if selected_name else []
        for name, color, symbol in focus_players:
            player_point = frame[frame["player"] == name]
            if player_point.empty:
                continue
            point = player_point.iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[point[x_col]],
                    y=[point[y_col]],
                    mode="markers+text" if label_mode == "highlight" else "markers",
                    text=[name] if label_mode == "highlight" else None,
                    textposition="top center",
                    textfont={"color": color, "size": 11},
                    marker={
                        "size": 33,
                        "color": "rgba(0,0,0,0)",
                        "line": {"color": color, "width": 3},
                        "symbol": symbol,
                    },
                    customdata=[[name]],
                    name=name,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        x_meta, y_meta = METRICS[x_col], METRICS[y_col]
        fig.update_layout(
            **_chart_layout(height=500, light_mode=light_mode),
            xaxis={
                "title": x_meta["label"].upper(),
                "tickformat": x_meta["tick"],
                "gridcolor": grid_color,
                "zeroline": False,
            },
            yaxis={
                "title": y_meta["label"].upper(),
                "tickformat": y_meta["tick"],
                "ticksuffix": y_meta.get("suffix", ""),
                "gridcolor": grid_color,
                "zeroline": False,
            },
            legend={"title": None, "orientation": "h", "x": 0, "y": 1.08},
            showlegend=False,
        )

        return plot_payload(
            fig,
            label=f'{input.play_type()} player volume and efficiency scatter plot',
            click_input="scatter_point",
        )

    @render.ui
    def player_heading():
        row = selected_row()
        if row is None:
            player = selected_player.get()
            if not player:
                return ui.tags.h2("No player selected")
            profile = selected_profile()
            if profile.empty:
                return ui.tags.h2(str(player))
            row = profile.sort_values("possessions", ascending=False).iloc[0]
        return ui.div(
            ui.tags.span("PINNED PLAYER", class_="eyebrow"),
            ui.div(
                team_logo_tag(row["team"]),
                ui.div(
                    ui.tags.h2(str(row["player"])),
                    ui.tags.span(f'{row["team"]} · {row["position"]}', class_="player-team"),
                    class_="player-heading-copy",
                ),
                class_="player-heading-content",
            ),
            class_="player-heading-stack",
        )

    @render.ui
    def player_snapshot():
        row = selected_row()
        if row is None:
            player = selected_player.get()
            if not player:
                return ui.div(
                    "Search for a player or click a point on the chart.",
                    class_="empty-state",
                )
            return ui.div(
                ui.tags.strong(f"No {input.play_type()} data available"),
                ui.tags.span(
                    f"{player} has no {input.play_type().lower()} stats for {input.season()}. "
                    "Try another play type."
                ),
                class_="empty-state player-no-data",
            )

        percentile = int(row["percentile"])
        return ui.div(
            ui.div(
                headshot_tag(
                    row["player_id"],
                    str(row["player"]),
                    class_name="player-avatar",
                    season=input.season(),
                    team=row["team"],
                ),
                ui.div(
                    ui.tags.span(ordinal(percentile), class_="percentile-number"),
                    ui.tags.span("EFFICIENCY PERCENTILE", class_="percentile-label"),
                ),
                class_="player-hero",
            ),
            ui.div(
                ui.div(ui.tags.span("PPP"), ui.tags.strong(f'{row["ppp"]:.3f}'), class_="stat-cell"),
                ui.div(ui.tags.span("FREQ"), ui.tags.strong(f'{row["frequency"]:.1%}'), class_="stat-cell"),
                ui.div(ui.tags.span("POSS"), ui.tags.strong(f'{int(row["possessions"]):,}'), class_="stat-cell"),
                ui.div(ui.tags.span("eFG%"), ui.tags.strong(f'{row["efg_pct"]:.1f}'), class_="stat-cell"),
                ui.div(ui.tags.span("SCORE%"), ui.tags.strong(f'{row["score_pct"]:.1f}'), class_="stat-cell"),
                ui.div(ui.tags.span("TOV%"), ui.tags.strong(f'{row["tov_pct"]:.1f}'), class_="stat-cell"),
                class_="player-stat-grid",
            ),
            ui.div(
                ui.tags.a("View full profile", href="#player-overview", class_="profile-link"),
                class_="player-card-foot",
            ),
            class_="player-snapshot",
        )

    @render.ui
    def overview_heading():
        player = selected_player.get()
        if not player:
            return ui.tags.h2("Select a player to view their profile")
        profile = selected_profile()
        if profile.empty:
            return ui.tags.h2(f"{player} has no data for {input.season()}")
        identity = profile.sort_values("possessions", ascending=False).iloc[0]
        return ui.div(
            headshot_tag(
                identity["player_id"],
                str(player),
                class_name="overview-headshot",
                season=input.season(),
                team=identity["team"],
            ),
            ui.div(
                ui.tags.h2(str(player)),
                ui.tags.span(
                    f'{identity["team"]} · {identity["position"]} · {input.season()}',
                    class_="overview-meta",
                ),
            ),
            class_="overview-heading-content",
        )

    @render.ui
    def player_insights():
        profile = selected_profile()
        row = selected_row()
        if profile.empty or row is None:
            return None
        best = profile.sort_values(["percentile", "possessions"], ascending=False).iloc[0]
        volume = profile.sort_values("possessions", ascending=False).iloc[0]
        league_frame = playtype_data[
            (playtype_data["season"].astype(str) == str(input.season()))
            & (playtype_data["play_type"] == input.play_type())
        ]
        league_ppp = weighted_average(league_frame, "ppp")
        difference = float(row["ppp"]) - league_ppp
        return ui.div(
            ui.div(
                ui.tags.span("BEST PLAY TYPE"),
                ui.tags.strong(str(best["play_type"])),
                ui.tags.small(f'{ordinal(int(best["percentile"]))} percentile'),
                class_="insight-item",
            ),
            ui.div(
                ui.tags.span("HIGHEST VOLUME"),
                ui.tags.strong(str(volume["play_type"])),
                ui.tags.small(f'{int(volume["possessions"]):,} possessions'),
                class_="insight-item",
            ),
            ui.div(
                ui.tags.span("VS LEAGUE AVERAGE"),
                ui.tags.strong(f'{difference:+.3f} PPP'),
                ui.tags.small("versus league average"),
                class_="insight-item",
            ),
            class_="player-insights",
        )

    @render.ui
    def overview_table():
        profile = selected_profile()
        if profile.empty:
            return ui.div(
                "Search for a player or click a point on the chart.",
                class_="empty-state overview-empty",
            )

        rows = []
        for _, row in profile.iterrows():
            rows.append(
                ui.tags.tr(
                    ui.tags.td(str(row["play_type"]), class_="overview-playtype", data_sort_value=str(row["play_type"])),
                    ui.tags.td(f'{row["frequency"]:.1%}', data_sort_value=str(row["frequency"])),
                    ui.tags.td(f'{int(row["possessions"]):,}', data_sort_value=str(row["possessions"])),
                    ui.tags.td(f'{row["ppp"]:.3f}', class_="overview-ppp", data_sort_value=str(row["ppp"])),
                    ui.tags.td(str(int(row["percentile"])), data_sort_value=str(row["percentile"])),
                    ui.tags.td(f'{row["efg_pct"]:.1f}%', data_sort_value=str(row["efg_pct"])),
                    ui.tags.td(f'{row["score_pct"]:.1f}%', data_sort_value=str(row["score_pct"])),
                    ui.tags.td(f'{row["tov_pct"]:.1f}%', data_sort_value=str(row["tov_pct"])),
                )
            )
        return ui.div(
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th(sortable_header("PLAY TYPE", 0)),
                        ui.tags.th(sortable_header("FREQ", 1, title=METRIC_DEFINITIONS["frequency"])),
                        ui.tags.th(sortable_header("POSS", 2, title=METRIC_DEFINITIONS["possessions"])),
                        ui.tags.th(sortable_header("PPP", 3, title=METRIC_DEFINITIONS["ppp"])),
                        ui.tags.th(sortable_header("PCTL", 4, title=METRIC_DEFINITIONS["percentile"])),
                        ui.tags.th(sortable_header("eFG%", 5, title=METRIC_DEFINITIONS["efg_pct"])),
                        ui.tags.th(sortable_header("SCORE%", 6, title=METRIC_DEFINITIONS["score_pct"])),
                        ui.tags.th(sortable_header("TOV%", 7, title=METRIC_DEFINITIONS["tov_pct"])),
                    )
                ),
                ui.tags.tbody(*rows),
                class_="overview-table sortable-table",
            ),
            class_="overview-table-wrap",
        )

    @render_plotly_json
    def overview_radar():
        profile = selected_profile()
        light_mode = input.color_mode() == "light"
        fig = go.Figure()
        if profile.empty:
            fig.add_annotation(
                text="Select a player",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font={"size": 14, "color": "#5B6D62" if light_mode else COLORS["muted"]},
            )
            fig.update_layout(**_chart_layout(height=390, light_mode=light_mode))
            return plot_payload(fig, label="No player selected for the playtype radar")

        identity = profile.sort_values("possessions", ascending=False).iloc[0]
        color = team_color_for(identity["team"])
        theta = profile["play_type"].astype(str).tolist()
        radii = profile["percentile"].astype(float).tolist()
        custom = profile[["ppp", "possessions", "frequency"]].to_numpy().tolist()
        theta.append(theta[0])
        radii.append(radii[0])
        custom.append(custom[0])
        fig.add_trace(
            go.Scatterpolar(
                r=radii,
                theta=theta,
                customdata=custom,
                mode="lines+markers",
                fill="toself",
                line={"color": color, "width": 2},
                marker={"color": color, "size": 6},
                fillcolor=color_with_alpha(color, 0.18),
                hovertemplate=(
                    "<b>%{theta}</b><br>Percentile %{r:.0f}<br>"
                    "PPP %{customdata[0]:.3f}<br>Possessions %{customdata[1]:,.0f}<br>"
                    "Frequency %{customdata[2]:.1%}<extra></extra>"
                ),
                showlegend=False,
            )
        )
        radar_layout = _chart_layout(height=390, light_mode=light_mode)
        radar_layout["margin"] = {"l": 55, "r": 55, "t": 35, "b": 35}
        fig.update_layout(
            **radar_layout,
            polar={
                "bgcolor": "rgba(0,0,0,0)",
                "radialaxis": {
                    "range": [0, 100],
                    "tickvals": [25, 50, 75, 100],
                    "gridcolor": "rgba(44,70,55,.14)" if light_mode else COLORS["grid"],
                    "linecolor": "rgba(0,0,0,0)",
                },
                "angularaxis": {
                    "gridcolor": "rgba(44,70,55,.14)" if light_mode else COLORS["grid"],
                    "linecolor": "rgba(0,0,0,0)",
                },
            },
        )
        return plot_payload(
            fig,
            label=f"{selected_player.get()} playtype percentile radar for {input.season()}",
        )

    @render.ui
    def trend_heading():
        player = selected_player.get()
        if not player:
            return ui.tags.h2("Select a player to view season history")
        return ui.tags.h2(f"{player} · {input.play_type()}")

    @render_plotly_json
    def season_trend():
        player = selected_player.get()
        metric = str(input.trend_metric() or "ppp")
        light_mode = input.color_mode() == "light"
        fig = go.Figure()
        if not player:
            fig.add_annotation(
                text="Select a player to compare seasons",
                x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                font={"size": 14, "color": "#5B6D62" if light_mode else COLORS["muted"]},
            )
            fig.update_layout(**_chart_layout(height=310, light_mode=light_mode))
            return plot_payload(fig, label="No player selected for season trend")

        history = playtype_data[
            (playtype_data["player"] == player)
            & (playtype_data["play_type"] == input.play_type())
        ].sort_values("season")
        if history.empty:
            fig.add_annotation(text="No season history available", x=0.5, y=0.5, showarrow=False)
        else:
            color = team_color_for(history.iloc[-1]["team"])
            fig.add_trace(go.Scatter(
                x=history["season"], y=history[metric], mode="lines+markers",
                line={"color": color, "width": 3}, marker={"color": color, "size": 8},
                customdata=history[["team", "possessions", "ppp", "frequency", "percentile"]],
                hovertemplate=(
                    "<b>%{x}</b> · %{customdata[0]}<br>Value %{y}<br>"
                    "PPP %{customdata[2]:.3f}<br>Frequency %{customdata[3]:.1%}<br>"
                    "Possessions %{customdata[1]:,.0f}<extra></extra>"
                ), showlegend=False,
            ))
        metric_meta = METRICS.get(metric, {"label": "Efficiency percentile", "tick": ".0f"})
        fig.update_layout(
            **_chart_layout(height=310, light_mode=light_mode),
            xaxis={"title": "SEASON", "gridcolor": "rgba(0,0,0,0)", "type": "category"},
            yaxis={
                "title": metric_meta["label"].upper(),
                "tickformat": metric_meta.get("tick", ".0f"),
                "ticksuffix": metric_meta.get("suffix", ""),
                "gridcolor": "rgba(44,70,55,.12)" if light_mode else COLORS["grid"],
                "rangemode": "tozero" if metric in {"possessions", "frequency", "percentile"} else "normal",
            },
        )
        return plot_payload(fig, label=f"{player} {input.play_type()} {metric_meta['label']} by season")

    @render.ui
    def comparison_context():
        return ui.tags.span(
            f"{input.season()} · {input.play_type()} selected · "
            "Points per possession (PPP) across play types",
            class_="metric-caption",
        )

    @render.ui
    def comparison_legend():
        items: list[object] = []
        season_frame = playtype_data[
            playtype_data["season"].astype(str) == str(input.season())
        ]
        series_colors = comparison_series_colors(season_frame, comparison_names())
        for index, name in enumerate(comparison_names()):
            color = series_colors[name]
            items.extend(
                [
                    ui.tags.span(
                        class_="compare-swatch",
                        style=f"background:{color}",
                    ),
                    ui.tags.span(name),
                ]
            )
        items.extend(
            [
                ui.tags.span(class_="compare-tick"),
                ui.tags.span("League avg"),
            ]
        )
        return ui.div(*items, class_="comparison-legend")

    @render.ui
    def comparison_matrix():
        names = comparison_names()
        if not names:
            return ui.div(
                "Search and add up to four players.",
                class_="comparison-empty",
            )

        season_frame = playtype_data[
            playtype_data["season"].astype(str) == str(input.season())
        ]
        current_frame = season_frame[season_frame["play_type"] == input.play_type()]
        current_rows = {
            str(row["player"]): row
            for _, row in current_frame[current_frame["player"].isin(names)].iterrows()
        }
        series_colors = comparison_series_colors(season_frame, names)

        headers = [ui.tags.th("STAT", class_="comparison-metric-heading")]
        for index, name in enumerate(names):
            player_rows = season_frame[season_frame["player"] == name]
            if player_rows.empty:
                headers.append(ui.tags.th(name))
                continue
            identity = player_rows.sort_values("possessions", ascending=False).iloc[0]
            color = series_colors[name]
            headers.append(
                ui.tags.th(
                    ui.div(
                        headshot_tag(
                            identity["player_id"],
                            name,
                            class_name="comparison-headshot",
                            season=input.season(),
                            team=identity["team"],
                        ),
                        ui.div(
                            ui.tags.strong(name),
                            ui.tags.span(str(identity["team"])),
                            class_="comparison-player-copy",
                        ),
                        class_="comparison-player-heading",
                    ),
                    style=f"--series-color:{color}",
                )
            )

        body_rows = []
        for key, label in COMPARISON_STATS:
            values = {
                name: float(current_rows[name][key])
                for name in names
                if name in current_rows and pd.notna(current_rows[name][key])
            }
            highest = max(values.values()) if values else None
            cells = [
                ui.tags.th(
                    ui.tags.button(
                        label,
                        type="button",
                        class_="comparison-sort-button",
                        data_metric=key,
                        title=f"Order players by {label}. {METRIC_DEFINITIONS.get(key, '')}",
                    ),
                    scope="row",
                )
            ]
            for name in names:
                value = values.get(name)
                is_highest = (
                    value is not None
                    and highest is not None
                    and np.isclose(value, highest)
                    and len(values) > 1
                )
                cells.append(
                    ui.tags.td(
                        ui.tags.span(
                            "N/A" if value is None else format_comparison_value(key, value),
                            class_="comparison-stat-value",
                        ),
                        class_="comparison-leader" if is_highest else None,
                    )
                )
            body_rows.append(ui.tags.tr(*cells))

        return ui.div(
            ui.tags.table(
                ui.tags.thead(ui.tags.tr(*headers)),
                ui.tags.tbody(*body_rows),
                class_=f"comparison-table comparison-count-{len(names)}",
            ),
            class_="comparison-table-wrap",
        )

    @render_plotly_json
    def profile_plot():
        season_frame = playtype_data[playtype_data["season"].astype(str) == str(input.season())]
        names = comparison_names()
        light_mode = input.color_mode() == "light"

        league = (
            season_frame.groupby("play_type", sort=False)
            .apply(lambda group: weighted_average(group, "ppp"), include_groups=False)
            .reindex(PLAY_TYPES)
        )
        order = list(PLAY_TYPES)[::-1]
        fig = go.Figure()
        series_colors = comparison_series_colors(season_frame, names)
        for index, name in enumerate(names):
            profile = season_frame[season_frame["player"] == name].set_index("play_type")
            color = series_colors[name]
            fig.add_trace(
                go.Bar(
                    y=order,
                    x=profile.reindex(order)["ppp"],
                    orientation="h",
                    name=name,
                    marker={"color": color, "line": {"width": 0}},
                    hovertemplate=f"<b>{name}</b><br>%{{y}} · %{{x:.3f}} PPP<extra></extra>",
                )
            )
        fig.add_trace(
            go.Scatter(
                y=order,
                x=league.reindex(order),
                mode="markers",
                name="League average",
                marker={"color": "#E8EEF5", "size": 7, "symbol": "line-ns", "line": {"width": 2}},
                hovertemplate="<b>League average</b><br>%{y} · %{x:.3f} PPP<extra></extra>",
            )
        )
        fig.update_layout(
            **_chart_layout(height=380, light_mode=light_mode),
            barmode="group",
            bargap=0.28,
            bargroupgap=0.05,
            showlegend=False,
            xaxis={
                "title": "POINTS PER POSSESSION",
                "tickformat": ".2f",
                "gridcolor": "rgba(44,70,55,.12)" if light_mode else COLORS["grid"],
                "zeroline": False,
            },
            yaxis={"title": None, "gridcolor": "rgba(0,0,0,0)", "automargin": True},
        )
        return plot_payload(
            fig,
            label=f"Playtype efficiency comparison for {', '.join(names)}",
        )

    @render.ui
    def leaderboard_metric():
        return ui.tags.span(
            f"{input.play_type()} · Points per possession (PPP)",
            class_="metric-caption",
        )

    @render.ui
    def leaderboard():
        frame = filtered_data().head(15)
        if frame.empty:
            return ui.div("No qualified players", class_="empty-state leaderboard-empty")

        rows = []
        for rank, (_, row) in enumerate(frame.iterrows(), start=1):
            rows.append(
                ui.tags.tr(
                    ui.tags.td(f"{rank:02d}", class_="rank-cell", data_sort_value=str(rank)),
                    ui.tags.td(
                        headshot_tag(
                            row["player_id"],
                            str(row["player"]),
                            class_name="leaderboard-headshot",
                            season=input.season(),
                            team=row["team"],
                        )
                    ),
                    ui.tags.td(
                        ui.tags.strong(str(row["player"])),
                        ui.tags.span(f'{row["team"]} · {row["position"]}', class_="table-meta"),
                        class_="name-cell",
                        data_sort_value=str(row["player"]),
                    ),
                    ui.tags.td(f'{row["ppp"]:.3f}', class_="number-cell", data_sort_value=str(row["ppp"])),
                    ui.tags.td(
                        ui.tags.span(f'{int(row["percentile"])}', class_="percentile-pill"),
                        class_="percentile-cell",
                        data_sort_value=str(row["percentile"]),
                    ),
                )
            )
        return ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("RK"),
                    ui.tags.th(""),
                    ui.tags.th(sortable_header("PLAYER", 2)),
                    ui.tags.th(sortable_header("PPP", 3, title=METRIC_DEFINITIONS["ppp"])),
                    ui.tags.th(sortable_header("PCTL", 4, title=METRIC_DEFINITIONS["percentile"])),
                )
            ),
            ui.tags.tbody(*rows),
            class_="leaderboard-table sortable-table",
        )


def _chart_layout(height: int, *, light_mode: bool = False) -> dict:
    return {
        "height": height,
        "margin": {"l": 58, "r": 24, "t": 32, "b": 62},
        "paper_bgcolor": COLORS["paper"],
        "plot_bgcolor": COLORS["paper"],
        "font": {
            "family": "Segoe UI, Arial, sans-serif",
            "color": "#5B6D62" if light_mode else COLORS["muted"],
            "size": 11,
        },
        "hoverlabel": {
            "bgcolor": "#111F2D",
            "bordercolor": "#2B3C4E",
            "font": {"family": "Segoe UI, Arial, sans-serif", "color": "#F6F8FA", "size": 12},
        },
        "hovermode": "closest",
        "dragmode": "pan",
        "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": COLORS["muted"], "activecolor": COLORS["text"]},
        "uirevision": "playtype-playground",
    }


www_dir = app_dir / "www"
app = App(app_ui, server, static_assets=www_dir)
_HEADSHOT_CACHE: dict[str, tuple[bytes, str]] = {}


def _fetch_headshot(url: str) -> tuple[bytes, str]:
    cached = _HEADSHOT_CACHE.get(url)
    if cached is not None:
        return cached
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 PlaytypePlayground/1.0"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        content_type = str(response.headers.get_content_type())
        if not content_type.startswith("image/"):
            raise ValueError("NBA headshot response was not an image")
        payload = response.read(6_000_001)
    if len(payload) > 6_000_000:
        raise ValueError("NBA headshot exceeded the size limit")
    result = (payload, content_type)
    _HEADSHOT_CACHE[url] = result
    return result


async def _season_headshot(request: Request) -> Response:
    team_id = int(request.path_params["team_id"])
    season_year = int(request.path_params["season_year"])
    player_id = int(request.path_params["player_id"])
    if team_id not in TEAM_IDS.values() or not 1990 <= season_year <= 2100 or player_id <= 0:
        return Response(status_code=404)
    url = REMOTE_SEASON_HEADSHOT_URL.format(
        team_id=team_id,
        season_year=season_year,
        player_id=player_id,
    )
    try:
        payload, content_type = await asyncio.to_thread(_fetch_headshot, url)
    except (OSError, ValueError, urllib.error.URLError):
        fallback_url = REMOTE_HEADSHOT_URL.format(player_id=player_id)
        try:
            payload, content_type = await asyncio.to_thread(_fetch_headshot, fallback_url)
        except (OSError, ValueError, urllib.error.URLError):
            return Response(status_code=404)
    return Response(
        payload,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


async def _latest_headshot(request: Request) -> Response:
    player_id = int(request.path_params["player_id"])
    if player_id <= 0:
        return Response(status_code=404)
    url = REMOTE_HEADSHOT_URL.format(player_id=player_id)
    try:
        payload, content_type = await asyncio.to_thread(_fetch_headshot, url)
    except (OSError, ValueError, urllib.error.URLError):
        return Response(status_code=404)
    return Response(
        payload,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


async def _robots(request: Request) -> PlainTextResponse:
    sitemap_url = f"{CANONICAL_URL}sitemap.xml"
    rules = (
        "User-agent: *\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: ChatGPT-User\nAllow: /\n\n"
        "User-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: Google-Extended\nAllow: /\n\n"
        f"Sitemap: {sitemap_url}\n"
    )
    return PlainTextResponse(rules)


async def _sitemap(request: Request) -> Response:
    urls = (CANONICAL_URL, f"{CANONICAL_URL}privacy.html", f"{CANONICAL_URL}terms.html")
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</urlset>"
    )
    return Response(xml, media_type="application/xml")


async def _not_found(request: Request, exc: Exception) -> HTMLResponse:
    return HTMLResponse((www_dir / "404.html").read_text(encoding="utf-8"), status_code=404)


app.starlette_app.routes.insert(-1, Route("/robots.txt", _robots, methods=["GET"]))
app.starlette_app.routes.insert(-1, Route("/sitemap.xml", _sitemap, methods=["GET"]))
app.starlette_app.routes.insert(
    -1,
    Route(
        "/headshots/{team_id:int}/{season_year:int}/{player_id:int}.png",
        _season_headshot,
        methods=["GET"],
    ),
)
app.starlette_app.routes.insert(
    -1,
    Route("/headshots/latest/{player_id:int}.png", _latest_headshot, methods=["GET"]),
)
app.starlette_app.add_exception_handler(404, _not_found)
