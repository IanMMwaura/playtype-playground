(function () {
  "use strict";

  function inputContainer(id) {
    const input = document.getElementById(id);
    if (!input) return null;
    return input.closest(".shiny-input-container, .form-group") || input;
  }

  function panel(title, className, items) {
    const section = document.createElement("section");
    section.className = `body-control-panel ${className}`;
    const heading = document.createElement("div");
    heading.className = "body-control-heading";
    heading.textContent = title;
    const grid = document.createElement("div");
    grid.className = "body-control-grid";
    items.filter(Boolean).forEach((item) => grid.appendChild(item));
    section.append(heading, grid);
    return section;
  }

  function moveControls() {
    if (document.body.classList.contains("body-controls-layout")) return;

    const context = document.querySelector(".context-strip");
    const scatter = document.getElementById("scatterplot");
    const snapshot = document.getElementById("player_snapshot");
    const comparison = document.getElementById("comparison_matrix");
    if (!context || !scatter || !snapshot || !comparison) {
      window.setTimeout(moveControls, 50);
      return;
    }

    document.body.classList.add("body-controls-layout");

    const hiddenControls = document.createElement("div");
    hiddenControls.className = "body-control-hidden";
    const usageTier = inputContainer("usage_tier");
    if (usageTier) hiddenControls.appendChild(usageTier);
    document.body.appendChild(hiddenControls);

    const filters = panel("Filters", "body-filter-controls", [
      inputContainer("season"),
      inputContainer("play_type"),
      inputContainer("team_filter"),
      inputContainer("position"),
      inputContainer("min_possessions"),
    ]);
    const filterActions = document.createElement("div");
    filterActions.className = "body-filter-actions";
    const reset = document.getElementById("reset");
    const source = document.querySelector(".sidebar-source");
    if (reset) filterActions.appendChild(reset);
    if (source) filterActions.appendChild(source);
    filters.appendChild(filterActions);
    context.insertAdjacentElement("afterend", filters);

    const playerSearch = panel("Player search", "body-player-controls", [
      inputContainer("highlight"),
    ]);
    snapshot.insertAdjacentElement("beforebegin", playerSearch);

    const chartItems = [
      inputContainer("x_metric"),
      inputContainer("y_metric"),
      inputContainer("label_mode"),
      inputContainer("headshots"),
      inputContainer("avg_overlay"),
      document.querySelector(".metric-glossary"),
    ];
    const chartSettings = panel("Chart settings", "body-chart-controls", chartItems);
    scatter.insertAdjacentElement("beforebegin", chartSettings);

    const comparisonMode = document.getElementById("comparison_season_mode");
    const comparisonStart = inputContainer("comparison_start");
    const comparisonEnd = inputContainer("comparison_end");
    const comparePlayers = panel("Choose players", "body-comparison-controls", [
      inputContainer("comparison_season_mode"),
      comparisonStart,
      comparisonEnd,
      inputContainer("compare_players"),
    ]);
    comparison.insertAdjacentElement("beforebegin", comparePlayers);
    const comparisonSeasonSelectors = document.getElementById("comparison_season_selectors");
    if (comparisonSeasonSelectors) {
      comparePlayers.insertAdjacentElement("afterend", comparisonSeasonSelectors);
    }

    function syncComparisonMode() {
      const hidden = Boolean(comparisonMode && comparisonMode.value !== "shared");
      comparePlayers.classList.toggle("comparison-mode-compact", hidden);
      [comparisonStart, comparisonEnd].forEach((control) => {
        if (control) control.hidden = hidden;
      });
    }
    if (comparisonMode) comparisonMode.addEventListener("change", syncComparisonMode);
    syncComparisonMode();

    const overviewMode = document.getElementById("overview_season_mode");
    const overviewStart = inputContainer("radar_start");
    const overviewEnd = inputContainer("radar_end");
    const overviewLayer = inputContainer("overview_layer_seasons");
    function syncOverviewMode() {
      const hidden = Boolean(overviewMode && overviewMode.value !== "span");
      [overviewStart, overviewEnd].forEach((control) => {
        if (control) control.hidden = hidden;
      });
      if (overviewLayer) {
        overviewLayer.hidden = Boolean(overviewMode && overviewMode.value === "single");
      }
    }
    if (overviewMode) overviewMode.addEventListener("change", syncOverviewMode);
    syncOverviewMode();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", moveControls, { once: true });
  } else {
    moveControls();
  }
})();
