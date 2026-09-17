const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "top",
      labels: {
        usePointStyle: true,
        padding: 18,
      },
    },
    tooltip: {
      padding: 12,
      cornerRadius: 10,
      displayColors: true,
    },
  },
};

function createTemperatureOverview(data) {
  new Chart(document.getElementById("temperatureOverview"), {
    type: "line",
    data: {
      labels: data.map(d => d.month),
      datasets: [
        {
          label: "Average temperature",
          data: data.map(d => d.average),
          borderWidth: 3,
          pointRadius: 4,
          tension: 0.25,
        },
        {
          label: "Warmest station",
          data: data.map(d => d.warmest?.value ?? null),
          borderWidth: 1.5,
          pointRadius: 3,
          borderDash: [6, 5],
          tension: 0.25,
        },
        {
          label: "Coldest station",
          data: data.map(d => d.coldest?.value ?? null),
          borderWidth: 1.5,
          pointRadius: 3,
          borderDash: [6, 5],
          tension: 0.25,
        },
      ],
    },
    options: {
      ...chartDefaults,
      interaction: {
        mode: "index",
        intersect: false,
      },
      scales: {
        x: {
          grid: { display: false },
          title: { display: true, text: "Month" },
        },
        y: {
          grid: { color: "#e9edf2" },
          title: { display: true, text: "Temperature (°C)" },
        },
      },
      plugins: {
        ...chartDefaults.plugins,
        tooltip: {
          ...chartDefaults.plugins.tooltip,
          callbacks: {
            afterBody(items) {
              const month = data[items[0].dataIndex];
              return [
                `Warmest: ${month.warmest?.station ?? "—"}`,
                `Coldest: ${month.coldest?.station ?? "—"}`,
              ];
            },
          },
        },
      },
    },
  });
}

function createProvinceComparison(canvasId, data, type, detailsId) {
  const isTemperature = type === "temperature";
  const actualKey = isTemperature ? "actual_temp" : "actual_precip";
  const normalKey = isTemperature ? "normal_temp" : "normal_precip";
  const unit = isTemperature ? "°C" : "mm";
  const yTitle = isTemperature ? "Temperature (°C)" : "Precipitation (mm)";
  const details = document.getElementById(detailsId);

  const chart = new Chart(document.getElementById(canvasId), {
    type: "bar",
    data: {
      labels: data.map(d => d.short_name),
      datasets: [
        {
          label: "2025",
          data: data.map(d => d[actualKey]),
          borderRadius: 4,
          borderWidth: 0,
          backgroundColor: "#4f78a8",
        },
        {
          label: "1991–2020 Normal",
          data: data.map(d => d[normalKey]),
          borderRadius: 4,
          borderWidth: 0,
          backgroundColor: "#aab4c0",
        },
      ],
    },
    options: {
      ...chartDefaults,
      interaction: {
        mode: "index",
        intersect: false,
      },
      scales: {
        x: {
          grid: { display: false },
          title: { display: true, text: "Province / territory" },
        },
        y: {
          grid: { color: "#e9edf2" },
          title: { display: true, text: yTitle },
        },
      },
      plugins: {
        ...chartDefaults.plugins,
        tooltip: {
          ...chartDefaults.plugins.tooltip,
          callbacks: {
            title(items) {
              return data[items[0].dataIndex].province;
            },
            label(item) {
              return `${item.dataset.label}: ${item.formattedValue} ${unit}`;
            },
            afterBody(items) {
              const row = data[items[0].dataIndex];
              return [`Represented stations: ${row.stations}`];
            },
          },
        },
      },
      onClick(event, elements) {
        if (!elements.length) return;
        const row = data[elements[0].index];
        details.innerHTML = `
          <strong>${row.province}</strong>
          <span>${row.stations} represented station${row.stations === 1 ? "" : "s"}</span>
          <span>2025: ${row[actualKey] ?? "—"} ${unit}</span>
          <span>1991–2020 normal: ${row[normalKey] ?? "—"} ${unit}</span>
        `;
        details.classList.add("visible");
      },
    },
  });

  return chart;
}

function createRanking(canvasId, data, label, unit) {
  const height = Math.max(520, data.length * 32);
  document.getElementById(canvasId).parentElement.style.height = `${height}px`;

  new Chart(document.getElementById(canvasId), {
    type: "bar",
    data: {
      labels: data.map(d => d.station),
      datasets: [{
        label,
        data: data.map(d => d.value),
        borderWidth: 0,
        borderRadius: 5,
      }],
    },
    options: {
      ...chartDefaults,
      indexAxis: "y",
      interaction: {
        mode: "nearest",
        intersect: true,
      },
      scales: {
        x: {
          grid: { color: "#e9edf2" },
          title: { display: true, text: `${label} (${unit})` },
        },
        y: {
          grid: { display: false },
          title: { display: true, text: "Weather station" },
        },
      },
      plugins: {
        ...chartDefaults.plugins,
        legend: { display: false },
        tooltip: {
          ...chartDefaults.plugins.tooltip,
          callbacks: {
            title(items) {
              const index = items[0].dataIndex;
              return `${data[index].station} (${data[index].province})`;
            },
            label(item) {
              return `${label}: ${item.formattedValue} ${unit}`;
            },
          },
        },
      },
    },
  });
}

function createMap(stations) {
  const map = L.map("map", {
    scrollWheelZoom: true,
  }).setView([56, -96], 4);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 18,
  }).addTo(map);

  const markers = [];
  let selectedMarker = null;

  stations.forEach(station => {
    const marker = L.circleMarker(
      [station.latitude, station.longitude],
      {
        radius: 7,
        weight: 2,
        fillOpacity: 0.95,
        className: "station-marker",
      }
    ).addTo(map);

    marker.bindTooltip(station.station, {
      direction: "top",
      offset: [0, -8],
    });

    marker.bindPopup(`
      <div class="popup-title">${station.station}</div>
      <div><strong>${station.province ?? ""}</strong></div>
      ${station.reference_city ? `<div>Reference city: ${station.reference_city}</div>` : ""}
      <div class="popup-muted">${station.latitude.toFixed(3)}, ${station.longitude.toFixed(3)}</div>
      <hr>
      <div><strong>2025 average temperature:</strong> ${station.temperature_2025 ?? "—"} °C</div>
      <div><strong>2025 precipitation:</strong> ${station.precipitation_2025 ?? "—"} mm</div>
      <div><strong>Temperature normal:</strong> ${station.temperature_normal ?? "—"} °C</div>
      <div><strong>Precipitation normal:</strong> ${station.precipitation_normal ?? "—"} mm</div>
    `);

    marker.on("click", () => {
      if (selectedMarker) {
        selectedMarker.setStyle({ radius: 7 });
      }
      marker.setStyle({ radius: 10 });
      selectedMarker = marker;
    });

    marker.on("popupclose", () => {
      // Keep the selected marker slightly larger until another station is clicked.
    });

    markers.push(marker);
  });

  if (markers.length) {
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.05));
  }
}

async function init() {
  try {
    const dataResponse = await fetch("data.json");

    if (!dataResponse.ok) {
      throw new Error(`Could not load data.json (${dataResponse.status})`);
    }

    const data = await dataResponse.json();

    createTemperatureOverview(data.temperature_overview);

    createProvinceComparison(
      "temperatureComparison",
      data.province_comparison,
      "temperature",
      "temperatureDetails"
    );

    createProvinceComparison(
      "precipitationComparison",
      data.province_comparison,
      "precipitation",
      "precipitationDetails"
    );

    createRanking(
      "temperatureRanking",
      data.temperature_ranking,
      "Annual mean temperature",
      "°C"
    );

    createRanking(
      "precipitationRanking",
      data.precipitation_ranking,
      "Annual precipitation",
      "mm"
    );

    createMap(data.map_stations);
  } catch (error) {
    console.error(error);
    document.querySelector("main").insertAdjacentHTML(
      "afterbegin",
      `<div class="card error-card">
        <strong>Could not load the dashboard data.</strong>
        <p>${error.message}</p>
        <p>Run <code>prepare_data.py</code> first and open the project through a local web server.</p>
      </div>`
    );
  }
}

init();
