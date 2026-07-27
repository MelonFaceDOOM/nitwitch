(function () {
  function readChartData(scriptId) {
    var el = document.getElementById(scriptId);
    if (!el) {
      return { labels: [], datasets: [] };
    }
    return JSON.parse(el.textContent);
  }

  var palette = [
    "#4C8B68",
    "#67397D",
    "#211626",
    "#8B5A2B",
    "#2F5D8C",
    "#A14A3A",
    "#5C6B3A",
  ];

  function colorize(payload) {
    var datasets = (payload.datasets || []).map(function (ds, i) {
      var color = palette[i % palette.length];
      return Object.assign({}, ds, {
        borderColor: color,
        backgroundColor: color,
      });
    });
    return {
      labels: payload.labels || [],
      datasets: datasets,
    };
  }

  function makeLineChart(canvasId, scriptId) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") {
      return;
    }
    var data = colorize(readChartData(scriptId));
    if (!data.labels.length) {
      return;
    }
    new Chart(canvas, {
      type: "line",
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
        },
        scales: {
          x: {
            ticks: { maxRotation: 45, minRotation: 0 },
          },
          y: {
            beginAtZero: true,
          },
        },
      },
    });
  }

  makeLineChart("ingestion-chart", "wmvi-ingestion-data");
  makeLineChart("is-en-chart", "wmvi-is-en-data");
  makeLineChart("term-chart", "wmvi-term-data");
  makeLineChart("podcast-transcriptions-chart", "wmvi-podcast-data");
  makeLineChart("youtube-transcriptions-chart", "wmvi-youtube-data");
})();
