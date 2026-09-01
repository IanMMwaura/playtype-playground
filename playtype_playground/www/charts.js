(function () {
  "use strict";

  let applyingUrlState = false;

  const stateFields = {
    season: "season",
    play: "play_type",
    team: "team_filter",
    usage: "usage_tier",
    min: "min_possessions",
    x: "x_metric",
    y: "y_metric",
    labels: "label_mode",
    player: "highlight",
    trend: "trend_metric",
  };

  function inputValue(id) {
    const element = document.getElementById(id);
    if (!element) return "";
    if (element.selectize) {
      return element.selectize.items.join(",");
    }
    return element.value || "";
  }

  function setInput(id, value) {
    const element = document.getElementById(id);
    if (!element || value == null) return;
    if (element.selectize) {
      const next = element.multiple ? value.split(",").filter(Boolean) : value;
      element.selectize.setValue(next);
      return;
    }
    const slider = window.jQuery && window.jQuery(element).data("ionRangeSlider");
    if (slider) {
      slider.update({ from: Number(value) });
      window.jQuery(element).trigger("change");
      return;
    }
    element.value = value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function applyUrlState() {
    const params = new URLSearchParams(window.location.search);
    if (!params.size) return;
    applyingUrlState = true;
    Object.entries(stateFields).forEach(([param, id]) => {
      if (params.has(param)) setInput(id, params.get(param));
    });
    if (params.has("compare")) setInput("compare_players", params.get("compare"));
    ["avg_overlay", "headshots"].forEach((id) => {
      if (!params.has(id)) return;
      const element = document.getElementById(id);
      if (!element) return;
      element.checked = params.get(id) === "1";
      element.dispatchEvent(new Event("change", { bubbles: true }));
    });
    if (params.has("positions")) {
      const selected = new Set(params.get("positions").split(","));
      document.querySelectorAll('input[name="position"]').forEach((element) => {
        element.checked = selected.has(element.value);
        element.dispatchEvent(new Event("change", { bubbles: true }));
      });
    }
    window.setTimeout(() => { applyingUrlState = false; }, 100);
  }

  function currentUrl() {
    const params = new URLSearchParams();
    Object.entries(stateFields).forEach(([param, id]) => {
      const value = inputValue(id);
      if (value) params.set(param, value);
    });
    const comparisons = inputValue("compare_players");
    if (comparisons) params.set("compare", comparisons);
    ["avg_overlay", "headshots"].forEach((id) => {
      const element = document.getElementById(id);
      if (element) params.set(id, element.checked ? "1" : "0");
    });
    const positions = Array.from(document.querySelectorAll('input[name="position"]:checked'))
      .map((element) => element.value);
    if (positions.length) params.set("positions", positions.join(","));
    return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
  }

  function updateUrl() {
    if (applyingUrlState) return;
    window.history.replaceState({}, "", currentUrl());
  }

  function sortTable(button) {
    const table = button.closest("table");
    const body = table && table.tBodies[0];
    if (!body) return;
    const column = Number(button.dataset.sortColumn);
    const ascending = button.dataset.direction !== "asc";
    const rows = Array.from(body.rows);
    rows.sort((left, right) => {
      const a = left.cells[column]?.dataset.sortValue || left.cells[column]?.textContent.trim() || "";
      const b = right.cells[column]?.dataset.sortValue || right.cells[column]?.textContent.trim() || "";
      const aNumber = Number(a);
      const bNumber = Number(b);
      const result = Number.isFinite(aNumber) && Number.isFinite(bNumber)
        ? aNumber - bNumber
        : a.localeCompare(b, undefined, { sensitivity: "base" });
      return ascending ? result : -result;
    });
    rows.forEach((row, index) => {
      body.appendChild(row);
      const rank = row.querySelector(".rank-cell");
      if (rank) rank.textContent = String(index + 1).padStart(2, "0");
    });
    table.querySelectorAll(".table-sort-button").forEach((item) => {
      item.removeAttribute("data-direction");
      item.setAttribute("aria-sort", "none");
    });
    button.dataset.direction = ascending ? "asc" : "desc";
    button.setAttribute("aria-sort", ascending ? "ascending" : "descending");
  }

  function downloadPlot(id, filename) {
    const plot = document.getElementById(id);
    if (!plot || !plot.data) return;
    window.Plotly.downloadImage(plot, {
      format: "png",
      filename,
      width: 1400,
      height: 900,
      scale: 1,
    });
  }

  async function downloadElement(button) {
    const target = document.querySelector(button.dataset.exportTarget || "");
    if (!target || !window.html2canvas) {
      setStatus("PNG export is unavailable. Reload the page and try again.", "error");
      return;
    }
    setStatus("Preparing PNG...", "busy");
    try {
      const background = getComputedStyle(target).backgroundColor || "#0d1925";
      const canvas = await window.html2canvas(target, {
        backgroundColor: background,
        scale: Math.max(2, window.devicePixelRatio || 1),
        useCORS: true,
        logging: false,
        ignoreElements: (element) => element.classList?.contains("card-export-button"),
      });
      const link = document.createElement("a");
      link.download = `${button.dataset.exportName || "playtype-playground-export"}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
      setStatus("PNG saved", "idle");
    } catch (_error) {
      setStatus("Could not create the PNG. Reload the page and try again.", "error");
    }
  }

  function setStatus(message, kind) {
    const status = document.getElementById("app_status");
    if (!status) return;
    status.textContent = message;
    status.dataset.kind = kind || "idle";
  }

  function registerDashboardEnhancements() {
    if (window.PlaytypePlaygroundEnhancementsRegistered) return;
    window.PlaytypePlaygroundEnhancementsRegistered = true;
    window.setTimeout(applyUrlState, 250);

    document.addEventListener("change", () => window.setTimeout(updateUrl, 50));
    document.addEventListener("click", async (event) => {
      const sortButton = event.target.closest(".table-sort-button");
      if (sortButton) sortTable(sortButton);

      const comparisonSort = event.target.closest(".comparison-sort-button");
      if (comparisonSort && window.Shiny) {
        window.Shiny.setInputValue("comparison_sort", comparisonSort.dataset.metric, { priority: "event" });
      }

      if (event.target.closest("#download_scatter_png")) {
        downloadPlot("scatterplot", "playtype-playground-landscape");
      }
      const exportButton = event.target.closest(".card-export-button");
      if (exportButton) {
        await downloadElement(exportButton);
      }
      const share = event.target.closest("#share_view");
      if (share) {
        const url = currentUrl();
        window.history.replaceState({}, "", url);
        try {
          await navigator.clipboard.writeText(url);
          share.textContent = "Link copied";
          window.setTimeout(() => { share.textContent = "Share view"; }, 1600);
        } catch (_error) {
          window.prompt("Copy this dashboard link", url);
        }
      }
    });
    document.addEventListener("shiny:busy", () => setStatus("Updating view...", "busy"));
    document.addEventListener("shiny:idle", () => setStatus("Dashboard ready", "idle"));
    document.addEventListener("shiny:error", () => {
      setStatus("Could not update this view. Change a filter and try again.", "error");
    });
    window.addEventListener("popstate", applyUrlState);
  }

  function registerPlaytypePlots() {
    if (
      !window.Shiny ||
      !window.Shiny.OutputBinding ||
      typeof window.Shiny.bindAll !== "function" ||
      !window.Plotly ||
      !window.jQuery
    ) {
      window.setTimeout(registerPlaytypePlots, 25);
      return;
    }

    if (window.PlaytypePlotBindingRegistered) {
      return;
    }
    window.PlaytypePlotBindingRegistered = true;

    class PlaytypePlotOutput extends window.Shiny.OutputBinding {
      find(scope) {
        return window.jQuery(scope).find(".playtype-plot-output");
      }

      async renderValue(element, payload) {
        if (!payload) {
          window.Plotly.purge(element);
          return;
        }

        if (typeof element.removeAllListeners === "function") {
          element.removeAllListeners("plotly_click");
        }

        element.setAttribute("aria-busy", "true");
        element.setAttribute("aria-label", payload.label || "Interactive chart");

        await window.Plotly.react(
          element,
          payload.data,
          payload.layout,
          payload.config
        );

        if (payload.clickInput) {
          element.on("plotly_click", function (event) {
            const point = event.points && event.points[0];
            const custom = point && point.customdata;
            const player = Array.isArray(custom) ? custom[0] : null;
            if (player) {
              window.Shiny.setInputValue(payload.clickInput, String(player), {
                priority: "event",
              });
            }
          });
        }

        element.setAttribute("aria-busy", "false");
      }

      resize(element) {
        if (element.data) {
          window.Plotly.Plots.resize(element);
        }
      }
    }

    window.Shiny.outputBindings.register(
      new PlaytypePlotOutput(),
      "playtype-playground.plot"
    );
    window.Shiny.bindAll(document.body);
    registerDashboardEnhancements();
  }

  registerPlaytypePlots();
})();
