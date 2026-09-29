(() => {
  const dataNode = document.getElementById('analytics-data');
  if (!dataNode) return;
  const payload = JSON.parse(dataNode.textContent || '{}');
  const palette = ['#1867c0', '#6f42c1', '#15847a', '#f2a900', '#d64a3a', '#4d7c8a', '#8a5a44', '#4c956c', '#9c6ade', '#e76f51'];
  const rows = value => Array.isArray(value) ? value : [];
  const values = (items, key) => rows(items).map(item => item[key]);
  const integerAxis = { beginAtZero: true, ticks: { precision: 0 } };
  const commonLineOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, scales: { y: integerAxis, x: { grid: { display: false } } } };
  const monthLabel = value => value ? new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short' }) : '';
  const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

  const noDataPlugin = {
    id: 'noData',
    afterDraw(chart) {
      const hasData = chart.data.datasets.some(dataset => rows(dataset.data).some(value => Number(value) > 0));
      if (hasData) return;
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      ctx.save();
      ctx.fillStyle = '#718197';
      ctx.font = '600 13px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText('No data for the selected filters', (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2);
      ctx.restore();
    }
  };
  if (!Chart.registry.plugins.get('noData')) Chart.register(noDataPlugin);

  const navigateWithFilter = (key, value) => {
    const url = new URL(window.location.href);
    if (value === undefined || value === null || value === '') url.searchParams.delete(key);
    else url.searchParams.set(key, value);
    url.searchParams.delete('page');
    window.location.href = url.toString();
  };

  const createChart = (id, config, clickFilter) => {
    const element = document.getElementById(id);
    if (!element) return null;
    if (clickFilter) {
      config.options = config.options || {};
      config.options.onClick = (_, active, chart) => {
        if (!active.length) return;
        const index = active[0].index;
        clickFilter(chart.data.labels[index], index, chart);
      };
      config.options.onHover = (event, active) => { event.native.target.style.cursor = active.length ? 'pointer' : 'default'; };
    }
    return new Chart(element, config);
  };

  createChart('sourceChart', {
    type: 'pie',
    data: { labels: values(payload.by_source, 'source_type'), datasets: [{ data: values(payload.by_source, 'total'), backgroundColor: palette, borderColor: '#fff', borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
  }, label => navigateWithFilter('source', label));

  createChart('yearChart', {
    type: 'bar', data: { labels: values(payload.by_year, 'year'), datasets: [{ label: 'Incidents', data: values(payload.by_year, 'total'), backgroundColor: '#1867c0', borderRadius: 7 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: integerAxis, x: { grid: { display: false } } } }
  }, label => navigateWithFilter('year', label));

  createChart('statusChart', {
    type: 'doughnut', data: { labels: values(payload.by_status, 'event_status'), datasets: [{ data: values(payload.by_status, 'total'), backgroundColor: palette, borderColor: '#fff', borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '58%', plugins: { legend: { position: 'bottom' } } }
  }, label => navigateWithFilter('status', label));

  createChart('trendChart', {
    type: 'line', data: { labels: rows(payload.by_month).map(item => monthLabel(item.month)), datasets: [{ label: 'Incidents', data: values(payload.by_month, 'total'), borderColor: '#1867c0', backgroundColor: 'rgba(24,103,192,.12)', fill: true, tension: .25, pointRadius: 2, pointHoverRadius: 5 }] },
    options: { ...commonLineOptions, plugins: { legend: { display: false } } }
  });

  const decision = payload.decision_support || {};
  createChart('decisionTrendChart', {
    type: 'line',
    data: {
      labels: rows(decision.daily_labels).map(value => value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''),
      datasets: [
        { label: 'Daily incidents', data: rows(decision.daily_values), borderColor: '#1867c0', backgroundColor: 'rgba(24,103,192,.10)', fill: true, tension: .18, pointRadius: 0, borderWidth: 1.5 },
        { label: '7-day average', data: rows(decision.rolling_average), borderColor: '#d64a3a', backgroundColor: '#d64a3a', fill: false, tension: .28, pointRadius: 0, borderWidth: 2.4 }
      ]
    },
    options: { ...commonLineOptions, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } }
  });
  createChart('agingChart', {
    type: 'bar',
    data: { labels: values(decision.aging, 'label'), datasets: [{ label: 'Unresolved incidents', data: values(decision.aging, 'total'), backgroundColor: ['#15847a', '#4d7c8a', '#f2a900', '#e76f51', '#d64a3a'], borderRadius: 7 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  });

  const categoryBar = (id, horizontal = false, source = payload.by_category) => createChart(id, {
    type: 'bar', data: { labels: values(source, 'category'), datasets: [{ label: 'Incidents', data: values(source, 'total'), backgroundColor: '#1867c0', borderRadius: 6 }] },
    options: { indexAxis: horizontal ? 'y' : 'x', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: horizontal ? { x: integerAxis, y: { grid: { display: false } } } : { y: integerAxis, x: { grid: { display: false }, ticks: { maxRotation: 55, minRotation: 25 } } } }
  }, label => navigateWithFilter('category', label));
  categoryBar('categoryChart');
  categoryBar('categoryRankingChart', true);
  categoryBar('commandCenterCategoryChart', true, payload.by_category);

  const stationBar = (id, source, key = 'police_station') => createChart(id, {
    type: 'bar', data: { labels: values(source, key), datasets: [{ label: 'Incidents', data: values(source, 'total'), backgroundColor: '#6f42c1', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  }, label => navigateWithFilter('station', label));
  stationBar('hotspotChart', payload.by_hotspot || []);
  stationBar('fieldHotspotChart', payload.by_field_hotspot || []);
  stationBar('areaTotalsChart', payload.by_area || []);
  stationBar('commandCenterDestinationsChart', payload.destinations || []);
  stationBar('dispatchStationChart', payload.station_totals || []);
  stationBar('categoryStationChart', payload.by_station || []);

  const hotspotTrend = payload.hotspot_trend || {};
  createChart('hotspotTrendChart', {
    type: 'line', data: { labels: rows(hotspotTrend.months).map(monthLabel), datasets: rows(hotspotTrend.datasets).map((series, index) => ({ label: series.area, data: series.values, borderColor: palette[index % palette.length], backgroundColor: palette[index % palette.length], fill: false, tension: .25, pointRadius: 1.5, pointHoverRadius: 5 })) },
    options: { ...commonLineOptions, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } }
  });

  const categoryArea = payload.category_area || {};
  createChart('categoryAreaChart', {
    type: 'bar', data: { labels: rows(categoryArea.areas), datasets: rows(categoryArea.datasets).map((series, index) => ({ label: series.category, data: series.values, backgroundColor: palette[index % palette.length], borderRadius: 3 })) },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, scales: { x: { ...integerAxis, stacked: true }, y: { stacked: true, grid: { display: false } } } }
  });

  const categoryTime = payload.category_time || {};
  createChart('categoryTimeChart', {
    type: 'line', data: { labels: rows(categoryTime.months).map(monthLabel), datasets: rows(categoryTime.monthly_datasets).map((series, index) => ({ label: series.category, data: series.values, borderColor: palette[index % palette.length], backgroundColor: palette[index % palette.length], tension: .25, fill: false, pointRadius: 1.5, pointHoverRadius: 5 })) },
    options: { ...commonLineOptions, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } }
  });
  createChart('categoryYearChart', {
    type: 'bar', data: { labels: rows(categoryTime.years), datasets: rows(categoryTime.yearly_datasets).map((series, index) => ({ label: series.category, data: series.values, backgroundColor: palette[index % palette.length], borderRadius: 3 })) },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, scales: { x: { stacked: true, grid: { display: false } }, y: { ...integerAxis, stacked: true } } }
  });
  createChart('categorySeasonChart', {
    type: 'line', data: { labels: rows(categoryTime.month_names), datasets: rows(categoryTime.seasonal_datasets).map((series, index) => ({ label: series.category, data: series.values, borderColor: palette[index % palette.length], backgroundColor: palette[index % palette.length], tension: .28, fill: false, pointRadius: 2, pointHoverRadius: 5 })) },
    options: { ...commonLineOptions, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } }
  });

  const timePatterns = payload.time_patterns || payload.time || payload;
  createChart('hourChart', {
    type: 'line', data: { labels: values(timePatterns.by_hour, 'label'), datasets: [{ label: 'Incidents', data: values(timePatterns.by_hour, 'total'), borderColor: '#15847a', backgroundColor: 'rgba(21,132,122,.13)', fill: true, tension: .25, pointRadius: 2 }] },
    options: { ...commonLineOptions, plugins: { legend: { display: false } } }
  });
  createChart('weekdayChart', {
    type: 'bar', data: { labels: values(timePatterns.by_weekday, 'weekday'), datasets: [{ label: 'Incidents', data: values(timePatterns.by_weekday, 'total'), backgroundColor: '#f2a900', borderRadius: 7 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: integerAxis, x: { grid: { display: false } } } }
  });
  createChart('categoryHourChart', {
    type: 'line', data: { labels: rows(timePatterns.by_hour).map(item => item.label), datasets: rows(timePatterns.category_hour).map((series, index) => ({ label: series.category, data: series.values, borderColor: palette[index % palette.length], backgroundColor: palette[index % palette.length], tension: .25, pointRadius: 1.5 })) },
    options: { ...commonLineOptions, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } }
  });

  const timeHeatmap = document.getElementById('timeHeatmap');
  if (timeHeatmap && rows(timePatterns.heatmap).length) {
    const allValues = timePatterns.heatmap.flatMap(row => row.values);
    const max = Math.max(...allValues, 1);
    const level = value => value === 0 ? 0 : Math.min(5, Math.max(1, Math.ceil(value / max * 5)));
    const head = `<thead><tr><th>Day</th>${rows(timePatterns.hours).map(hour => `<th>${escapeHtml(hour)}</th>`).join('')}</tr></thead>`;
    const body = `<tbody>${timePatterns.heatmap.map(row => `<tr><th>${escapeHtml(row.weekday)}</th>${row.values.map((value, index) => `<td class="heat-${level(value)}" title="${escapeHtml(row.weekday)} ${timePatterns.hours[index]}:00 — ${value.toLocaleString()} incidents">${value}</td>`).join('')}</tr>`).join('')}</tbody>`;
    timeHeatmap.innerHTML = `<div class="heatmap-grid"><table class="heatmap-table">${head}${body}</table></div>`;
  }

  createChart('commandCenterTrendChart', {
    type: 'line', data: { labels: rows(payload.by_month).map(item => monthLabel(item.month)), datasets: [{ label: 'Command Center incidents', data: values(payload.by_month, 'total'), borderColor: '#6f42c1', backgroundColor: 'rgba(111,66,193,.12)', fill: true, tension: .25 }] },
    options: { ...commonLineOptions, plugins: { legend: { display: false } } }
  });
  createChart('commandCenterStatusChart', {
    type: 'doughnut', data: { labels: values(payload.by_status, 'event_status'), datasets: [{ data: values(payload.by_status, 'total'), backgroundColor: palette, borderWidth: 2, borderColor: '#fff' }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
  });

  const branchBar = (id, source) => createChart(id, {
    type: 'bar', data: { labels: values(source, 'governing_branch'), datasets: [{ label: 'Incidents', data: values(source, 'total'), backgroundColor: '#1867c0', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  }, label => navigateWithFilter('branch', label));
  branchBar('dispatchBranchChart', payload.branch_totals || []);
  categoryBar('transferCategoryChart', true, payload.transfer_categories || []);

  createChart('qualityYearChart', {
    type: 'line',
    data: { labels: values(payload.yearly, 'year'), datasets: [
      { label: 'Raw Category %', data: values(payload.yearly, 'category_pct'), borderColor: palette[0], backgroundColor: palette[0], tension: .2 },
      { label: 'Category with Sub-Category fallback %', data: values(payload.yearly, 'analytical_category_pct'), borderColor: palette[1], backgroundColor: palette[1], tension: .2 },
      { label: 'Coordinate completeness %', data: values(payload.yearly, 'coordinate_pct'), borderColor: palette[2], backgroundColor: palette[2], tension: .2 }
    ] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100, ticks: { callback: value => `${value}%` } }, x: { grid: { display: false } } }, plugins: { legend: { position: 'bottom' } } }
  });
  createChart('qualitySourceChart', {
    type: 'bar',
    data: { labels: values(payload.by_source, 'label'), datasets: [
      { label: 'Raw Category %', data: values(payload.by_source, 'category_pct'), backgroundColor: palette[0] },
      { label: 'Category with fallback %', data: values(payload.by_source, 'analytical_category_pct'), backgroundColor: palette[1] },
      { label: 'Coordinates %', data: values(payload.by_source, 'coordinate_pct'), backgroundColor: palette[2] },
      { label: 'Station %', data: values(payload.by_source, 'station_pct'), backgroundColor: palette[3] }
    ] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100, ticks: { callback: value => `${value}%` } }, x: { grid: { display: false } } }, plugins: { legend: { position: 'bottom' } } }
  });

  categoryBar('stationCategoryChart', true, payload.by_category || []);
  createChart('stationStatusChart', {
    type: 'doughnut', data: { labels: values(payload.by_status, 'event_status'), datasets: [{ data: values(payload.by_status, 'total'), backgroundColor: palette, borderColor: '#fff', borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
  });
  createChart('stationTrendChart', {
    type: 'line', data: { labels: rows(payload.by_month).map(item => monthLabel(item.month)), datasets: [{ label: 'Incidents', data: values(payload.by_month, 'total'), borderColor: '#1867c0', backgroundColor: 'rgba(24,103,192,.12)', fill: true, tension: .25 }] },
    options: { ...commonLineOptions, plugins: { legend: { display: false } } }
  });
  createChart('categorySubcategoryChart', {
    type: 'bar', data: { labels: values(payload.by_sub_category, 'sub_category'), datasets: [{ label: 'Incidents', data: values(payload.by_sub_category, 'total'), backgroundColor: '#6f42c1', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  });
  createChart('categoryProfileTrendChart', {
    type: 'line', data: { labels: rows(payload.by_month).map(item => monthLabel(item.month)), datasets: [{ label: 'Incidents', data: values(payload.by_month, 'total'), borderColor: '#6f42c1', backgroundColor: 'rgba(111,66,193,.12)', fill: true, tension: .25 }] },
    options: { ...commonLineOptions, plugins: { legend: { display: false } } }
  });

  createChart('reportingTypeChart', {
    type: 'bar', data: { labels: values(payload.reporting_types, 'reporting_type'), datasets: [{ label: 'Incidents', data: values(payload.reporting_types, 'total'), backgroundColor: '#1867c0', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  });
  const closureChart = (id, source, key, filterKey) => createChart(id, {
    type: 'bar', data: { labels: values(source, key), datasets: [{ label: 'Closure rate', data: values(source, 'closed_pct'), backgroundColor: '#15847a', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: context => `${context.raw}% closed` } } }, scales: { x: { beginAtZero: true, max: 100, ticks: { callback: value => `${value}%` } }, y: { grid: { display: false } } } }
  }, label => navigateWithFilter(filterKey, label));
  closureChart('stationClosureChart', payload.station_closure || [], 'police_station', 'station');
  closureChart('categoryClosureChart', payload.category_closure || [], 'category', 'category');

  createChart('topLocationChart', {
    type: 'bar', data: { labels: values(payload.top_locations, 'incident_location'), datasets: [{ label: 'Incidents', data: values(payload.top_locations, 'total'), backgroundColor: '#6f42c1', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  });
  const categoryLocation = payload.category_location || {};
  createChart('categoryLocationChart', {
    type: 'bar', data: { labels: rows(categoryLocation.locations), datasets: rows(categoryLocation.datasets).map((series, index) => ({ label: series.category, data: series.values, backgroundColor: palette[index % palette.length], borderRadius: 3 })) },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, scales: { x: { ...integerAxis, stacked: true }, y: { stacked: true, grid: { display: false } } } }
  });

  const forecast = payload.forecast || {};
  createChart('forecastChart', {
    type: 'line', data: { labels: rows(forecast.labels).map(monthLabel), datasets: [
      { label: 'Actual incidents', data: rows(forecast.actual), borderColor: palette[0], backgroundColor: 'rgba(24,103,192,.12)', fill: false, tension: .2, pointRadius: 2 },
      { label: 'Three-month baseline', data: rows(forecast.baseline), borderColor: palette[3], backgroundColor: palette[3], borderDash: [6,4], fill: false, tension: .2, pointRadius: 1 },
      { label: 'Projected incidents', data: rows(forecast.forecast), borderColor: palette[2], backgroundColor: 'rgba(21,132,122,.14)', borderDash: [3,3], fill: false, tension: .2, pointRadius: 3 }
    ] },
    options: { ...commonLineOptions, plugins: { legend: { position: 'bottom' } } }
  });
  createChart('themeChart', {
    type: 'bar', data: { labels: values(payload.themes, 'term'), datasets: [{ label: 'Mentions', data: values(payload.themes, 'total'), backgroundColor: '#4d7c8a', borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  });

  const mapElement = document.getElementById('incidentMap');
  const initializeIncidentMap = input => {
    if (!mapElement || typeof L === 'undefined') return;

    const response = Array.isArray(input) ? { points: input, metadata: {} } : (input || {});
    const metadata = { ...(response.metadata || {}) };
    const ugandaBounds = metadata.bounds || { min_lat: -1.6, max_lat: 4.5, min_lon: 29.4, max_lon: 35.1 };
    const isValidCoordinate = item => {
      const latitude = Number(item.latitude);
      const longitude = Number(item.longitude);
      return Number.isFinite(latitude)
        && Number.isFinite(longitude)
        && !(latitude === 0 && longitude === 0)
        && latitude >= Number(ugandaBounds.min_lat)
        && latitude <= Number(ugandaBounds.max_lat)
        && longitude >= Number(ugandaBounds.min_lon)
        && longitude <= Number(ugandaBounds.max_lon);
    };
    const categoryFor = item => String(
      item.map_category || item.category || item.sub_category || 'Uncategorised'
    ).trim() || 'Uncategorised';
    const mapItems = rows(response.points).filter(isValidCoordinate);

    const categoryColors = window.IncidentCategoryColors || {
      keyFor: category => String(category || 'Uncategorised').trim().toUpperCase(),
      colorFor: () => '#2563eb',
      descriptionFor: category => `Mapped coordinates classified as ${category || 'Uncategorised'}.`,
    };
    const canonicalCategoryKey = categoryColors.keyFor;
    const categoryColor = (category, item = null) => item?.category_colour || categoryColors.colorFor(category);
    const categoryDescription = categoryColors.descriptionFor;

    const cleanMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
    });
    const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    });
    const map = L.map(mapElement, {
      preferCanvas: true,
      layers: [cleanMap],
      zoomControl: true,
      minZoom: 6
    }).setView([1.3733, 32.2903], 7);

    const clusterIcon = group => {
      const childMarkers = group.getAllChildMarkers();
      const total = childMarkers.length;
      const categoryCounts = new Map();
      childMarkers.forEach(marker => {
        const categoryKey = marker.options.mapCategoryKey || 'UNCATEGORISED';
        const record = categoryCounts.get(categoryKey) || { total: 0, color: marker.options.mapColor || '#94a3b8' };
        record.total += 1;
        categoryCounts.set(categoryKey, record);
      });
      const ranked = [...categoryCounts.entries()].sort((a, b) => b[1].total - a[1].total);
      const shown = ranked.slice(0, 5);
      const shownTotal = shown.reduce((sum, [, value]) => sum + value.total, 0);
      let cursor = 0;
      const segments = shown.map(([, value]) => {
        const start = cursor;
        cursor += (value.total / total) * 100;
        return `${value.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
      });
      if (shownTotal < total) segments.push(`#cbd5e1 ${cursor.toFixed(2)}% 100%`);
      const size = total >= 1000 ? 'xl' : total >= 250 ? 'lg' : total >= 50 ? 'md' : 'sm';
      return L.divIcon({
        html: `<div class="category-cluster-ring" style="background:conic-gradient(${segments.join(',')})"><span>${total.toLocaleString()}</span></div>`,
        className: `incident-cluster category-cluster incident-cluster-${size}`,
        iconSize: L.point(50, 50)
      });
    };

    const cluster = typeof L.markerClusterGroup === 'function'
      ? L.markerClusterGroup({
          chunkedLoading: true,
          chunkInterval: 150,
          chunkDelay: 30,
          showCoverageOnHover: false,
          maxClusterRadius: 48,
          spiderfyOnMaxZoom: true,
          disableClusteringAtZoom: 16,
          iconCreateFunction: clusterIcon
        })
      : L.layerGroup();

    const markerRecords = [];
    const markerRecordsByIdentity = new Map();
    const incidentIdentity = item => {
      if (item && item.id != null && String(item.id).trim()) return `id:${item.id}`;
      return [item?.source_type, item?.producer_id, item?.event_id]
        .map(value => String(value || '').trim().toUpperCase())
        .join(':');
    };
    const activeCategories = new Set();
    const statusClass = status => {
      const normalized = String(status || '').trim().toUpperCase();
      if (['CLOSED', 'DELIVERED', 'FED BACK'].includes(normalized)) return 'status-resolved';
      if (['DISPATCHED', 'ARRIVED', 'ACCEPTED'].includes(normalized)) return 'status-active';
      if (['RECEIVED', 'DISPATCHING', 'PENDING CLOSURE'].includes(normalized)) return 'status-pending';
      return 'status-neutral';
    };
    const profileLink = (kind, value, label) => value
      ? `<a class="map-popup-link" href="/analytics/${kind}/${encodeURIComponent(value)}/">${escapeHtml(label || value)}</a>`
      : '—';

    const createMarkerRecord = item => {
      if (!isValidCoordinate(item)) return null;
      const category = categoryFor(item);
      const categoryKey = item.category_key || canonicalCategoryKey(category);
      const selectionKey = category;
      const color = categoryColor(category, item);
      const latitude = Number(item.latitude);
      const longitude = Number(item.longitude);
      const marker = L.circleMarker([latitude, longitude], {
        radius: 7,
        color: '#ffffff',
        fillColor: color,
        fillOpacity: .92,
        weight: 2,
        pane: 'markerPane',
        mapCategory: category,
        mapCategoryKey: categoryKey,
        mapColor: color
      });
      const reported = item.reported_at ? new Date(item.reported_at).toLocaleString() : 'Not recorded';
      const station = item.police_station || item.governing_branch || '';
      const location = item.incident_location || 'Location not recorded';
      const status = item.event_status || 'Status not recorded';
      const rawCategory = String(item.category || '').trim();
      const rawSubCategory = String(item.sub_category || '').trim();
      const subCategory = rawSubCategory && (!rawCategory || rawSubCategory.toUpperCase() !== category.toUpperCase())
        ? `<div class="map-popup-row"><i class="fa-solid fa-tags"></i><span><strong>Sub-Category:</strong> ${escapeHtml(rawSubCategory)}</span></div>`
        : '';
      const caseNature = item.case_nature
        ? `<div class="map-popup-row"><i class="fa-solid fa-layer-group"></i><span><strong>Case Nature:</strong> ${escapeHtml(item.case_nature)}</span></div>`
        : '';
      const confidence = item.confidence != null
        ? `<span class="map-popup-meta-item">Confidence ${Math.round(Number(item.confidence) * 100)}%</span>`
        : '';
      const coordinateText = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
      const categoryAnalysis = category && category !== 'Uncategorised'
        ? profileLink('categories', category, 'Open category analysis')
        : '';
      marker.bindTooltip(`${escapeHtml(category)} · ${escapeHtml(station || location)}`, {
        direction: 'top',
        opacity: .94,
        sticky: true
      });
      marker.bindPopup(`
        <div class="incident-popup">
          <div class="map-popup-category"><span class="map-popup-dot" style="background:${color}"></span>${escapeHtml(category)}</div>
          ${subCategory}
          <div class="map-popup-status ${statusClass(status)}">${escapeHtml(status)}</div>
          <div class="map-popup-row"><i class="fa-solid fa-location-dot"></i><span>${escapeHtml(location)}</span></div>
          <div class="map-popup-row"><i class="fa-solid fa-building-shield"></i><span>${profileLink('stations', station, station || 'No station')}</span></div>
          ${caseNature}
          <div class="map-popup-row"><i class="fa-regular fa-clock"></i><span><strong>Reported:</strong> ${escapeHtml(reported)}</span></div>
          <div class="map-popup-row"><i class="fa-solid fa-database"></i><span><strong>Data source:</strong> ${escapeHtml([item.source_type, item.origin].filter(Boolean).join(' · ') || 'Not recorded')}</span></div>
          <div class="map-popup-row"><i class="fa-solid fa-crosshairs"></i><span><strong>Coordinates:</strong> ${coordinateText}</span></div>
          <div class="map-popup-meta">
            <span class="map-popup-meta-item">${escapeHtml(item.source_type || 'Incident')}</span>
            <span class="map-popup-meta-item">${escapeHtml(item.event_id || '')}</span>
            ${confidence}
          </div>
          <div class="map-popup-actions">
            ${categoryAnalysis}
            ${station ? profileLink('stations', station, 'Open station profile') : ''}
            <button type="button" class="map-popup-button copy-coordinate" data-coordinate="${coordinateText}">Copy coordinates</button>
            <a class="map-popup-link" href="https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=17/${latitude}/${longitude}" target="_blank" rel="noopener">Open location</a>
          </div>
        </div>
      `, { maxWidth: 360, minWidth: 285 });
      return { marker, item, category, categoryKey, selectionKey, color, identity: incidentIdentity(item) };
    };

    mapItems.forEach(item => {
      const record = createMarkerRecord(item);
      if (record) {
        markerRecords.push(record);
        markerRecordsByIdentity.set(record.identity, record);
        activeCategories.add(record.selectionKey);
      }
    });
    const seenIncidentIdentities = new Set(markerRecordsByIdentity.keys());
    document.querySelectorAll('#liveIncidentRows [data-incident-identity]').forEach(row => {
      if (row.dataset.incidentIdentity) seenIncidentIdentities.add(row.dataset.incidentIdentity);
    });

    const heat = typeof L.heatLayer === 'function'
      ? L.heatLayer([], {
          radius: 24,
          blur: 20,
          maxZoom: 13,
          minOpacity: .28,
          gradient: { .2: '#2563eb', .45: '#22c55e', .65: '#facc15', .82: '#f97316', 1: '#dc2626' }
        })
      : null;

    const categorySummary = () => {
      const counts = new Map();
      markerRecords.forEach(record => {
        const existing = counts.get(record.selectionKey) || {
          key: record.selectionKey,
          category: record.category,
          total: 0,
          color: record.color
        };
        existing.total += 1;
        counts.set(record.selectionKey, existing);
      });
      return [...counts.values()]
        .sort((a, b) => b.total - a.total || a.category.localeCompare(b.category));
    };
    const currentRecords = () => markerRecords.filter(record => activeCategories.has(record.selectionKey));
    const liveFilters = new URLSearchParams(window.location.search);
    const matchesLiveFilters = item => {
      const exact = (parameter, value) => {
        const expected = liveFilters.get(parameter);
        return !expected || String(value || '') === expected;
      };
      if (!exact('source', item.source_type)) return false;
      if (!exact('status', item.event_status)) return false;
      if (!exact('station', item.police_station)) return false;
      if (!exact('branch', item.governing_branch)) return false;
      if (!exact('category', categoryFor(item))) return false;
      if (!exact('sub_category', item.sub_category)) return false;
      if (!exact('origin', item.origin)) return false;

      const reportedDate = String(item.reported_at || '').slice(0, 10);
      const year = liveFilters.get('year');
      if (year && !reportedDate.startsWith(`${year}-`)) return false;
      const dateFrom = liveFilters.get('date_from');
      const dateTo = liveFilters.get('date_to');
      if (dateFrom && (!reportedDate || reportedDate < dateFrom)) return false;
      if (dateTo && (!reportedDate || reportedDate > dateTo)) return false;

      const commandCenter = liveFilters.get('command_center');
      const isCommandCenter = [item.police_station, item.governing_branch]
        .some(value => String(value || '').trim().toUpperCase() === 'COMMAND CENTER');
      if (commandCenter === 'only' && !isCommandCenter) return false;
      if (commandCenter === 'exclude' && isCommandCenter) return false;

      const coordinate = liveFilters.get('coordinate');
      const hasCoordinatePair = item.latitude !== null && item.latitude !== undefined && item.latitude !== ''
        && item.longitude !== null && item.longitude !== undefined && item.longitude !== '';
      if (coordinate === 'mapped' && !hasCoordinatePair) return false;
      if (coordinate === 'unmapped' && hasCoordinatePair) return false;

      const query = String(liveFilters.get('q') || '').trim().toLowerCase();
      if (query) {
        const searchable = [
          item.event_id, item.incident_location, item.description, item.police_station,
          item.governing_branch, item.category, item.sub_category, item.camera_id
        ].map(value => String(value || '').toLowerCase()).join(' ');
        if (!searchable.includes(query)) return false;
      }
      return true;
    };
    let layerMode = 'points';

    const applyLayerMode = () => {
      if (map.hasLayer(cluster)) map.removeLayer(cluster);
      if (heat && map.hasLayer(heat)) map.removeLayer(heat);
      if (layerMode === 'points' || layerMode === 'both') cluster.addTo(map);
      if (heat && (layerMode === 'heat' || layerMode === 'both')) heat.addTo(map);
      document.querySelectorAll('.map-mode-button').forEach(button => {
        button.classList.toggle('active', button.dataset.mode === layerMode);
      });
    };

    let summaryNode = null;
    const updateMapSummary = records => {
      if (!summaryNode) return;
      const categoryCounter = new Map();
      const stationCounter = new Map();
      let latest = null;
      records.forEach(record => {
        const categoryEntry = categoryCounter.get(record.selectionKey) || { label: record.category, total: 0 };
        categoryEntry.total += 1;
        categoryCounter.set(record.selectionKey, categoryEntry);
        const station = record.item.police_station || record.item.governing_branch || 'Unknown area';
        stationCounter.set(station, (stationCounter.get(station) || 0) + 1);
        const date = record.item.reported_at ? new Date(record.item.reported_at) : null;
        if (date && (!latest || date > latest)) latest = date;
      });
      const topCategory = [...categoryCounter.values()].sort((a, b) => b.total - a.total)[0] || { label: '—', total: 0 };
      const topStation = [...stationCounter.entries()].sort((a, b) => b[1] - a[1])[0] || ['—', 0];
      const filteredTotal = Number(metadata.filtered_total || markerRecords.length);
      const mappedTotal = Number(metadata.mapped_total || markerRecords.length);
      const coverage = filteredTotal ? Math.round((mappedTotal / filteredTotal) * 1000) / 10 : 0;
      summaryNode.innerHTML = `
        <div class="map-summary-title">Category map snapshot</div>
        <div class="map-summary-grid map-summary-grid-six">
          <div><strong>${records.length.toLocaleString()}</strong><span>Visible coordinates</span></div>
          <div><strong>${categoryCounter.size.toLocaleString()}</strong><span>Visible categories</span></div>
          <div><strong>${topCategory.total.toLocaleString()}</strong><span>${escapeHtml(topCategory.label)}</span></div>
          <div><strong>${topStation[1].toLocaleString()}</strong><span>${escapeHtml(topStation[0])}</span></div>
          <div><strong>${coverage}%</strong><span>Coordinate coverage</span></div>
          <div><strong>${latest ? latest.toLocaleDateString() : '—'}</strong><span>Latest mapped report</span></div>
        </div>
        ${metadata.truncated ? '<div class="map-summary-warning">The map is showing the newest coordinate records up to the configured limit.</div>' : ''}`;
    };

    const updateLayers = () => {
      cluster.clearLayers();
      const records = currentRecords();
      records.forEach(record => cluster.addLayer(record.marker));
      if (heat && typeof heat.setLatLngs === 'function') {
        heat.setLatLngs(records.map(record => [
          Number(record.item.latitude),
          Number(record.item.longitude),
          .35 + Math.min(1, records.length / 5000) * .35
        ]));
      }
      updateMapSummary(records);
      applyLayerMode();
    };

    const baseLayers = { 'Clean administrative map': cleanMap, 'Street map': streetMap };
    L.control.layers(baseLayers, {}, { collapsed: true, position: 'topright' }).addTo(map);

    const summaryControl = L.control({ position: 'topright' });
    summaryControl.onAdd = () => {
      summaryNode = L.DomUtil.create('div', 'map-decision-summary');
      L.DomEvent.disableClickPropagation(summaryNode);
      return summaryNode;
    };
    summaryControl.addTo(map);

    let legendNode = null;
    let legendSearch = '';
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = () => {
      legendNode = L.DomUtil.create('div', 'map-legend category-map-legend');
      L.DomEvent.disableClickPropagation(legendNode);
      L.DomEvent.disableScrollPropagation(legendNode);
      return legendNode;
    };
    legend.addTo(map);

    const filterLegendItems = () => {
      if (!legendNode) return;
      const needle = legendSearch.trim().toLowerCase();
      legendNode.querySelectorAll('.map-legend-item').forEach(item => {
        const label = String(item.dataset.categoryLabel || '').toLowerCase();
        item.hidden = Boolean(needle && !label.includes(needle));
      });
    };

    const renderLegend = () => {
      if (!legendNode) return;
      const categories = categorySummary();
      const availableKeys = new Set(categories.map(item => item.key));
      [...activeCategories].forEach(key => {
        if (!availableKeys.has(key)) activeCategories.delete(key);
      });
      const allTotal = categories.reduce((sum, item) => sum + item.total, 0);
      legendNode.innerHTML = `
        <div class="map-legend-head">
          <div><strong>Crime / incident categories</strong><small>Every coordinate uses its resolved CSV Category. Identical category names always use the same stable colour.</small></div>
        </div>
        <div class="map-legend-toolbar">
          <input type="search" class="map-legend-search" placeholder="Search category" value="${escapeHtml(legendSearch)}" aria-label="Search incident category">
          <div class="map-legend-actions">
            <button type="button" data-action="all">All</button>
            <button type="button" data-action="top">Top 10</button>
            <button type="button" data-action="clear">Clear</button>
          </div>
        </div>
        <div class="map-legend-items">
          ${categories.map(item => {
            const encoded = encodeURIComponent(item.key);
            const percent = allTotal ? ((item.total / allTotal) * 100).toFixed(1) : '0.0';
            const description = categoryDescription(item.category);
            return `
              <button type="button" class="map-legend-item ${activeCategories.has(item.key) ? 'active' : 'muted'}" data-category-key="${encoded}" data-category-label="${escapeHtml(item.category)}" title="Toggle ${escapeHtml(item.category)}">
                <i style="background:${item.color}"></i>
                <span><strong>${escapeHtml(item.category)}</strong><small>${escapeHtml(description)}</small></span>
                <b>${item.total.toLocaleString()} <em>${percent}%</em></b>
              </button>`;
          }).join('')}
        </div>
        <div class="map-legend-foot">${activeCategories.size.toLocaleString()} of ${categories.length.toLocaleString()} categories visible</div>`;

      const search = legendNode.querySelector('.map-legend-search');
      if (search) {
        search.addEventListener('input', event => {
          legendSearch = event.target.value;
          filterLegendItems();
        });
      }
      legendNode.querySelectorAll('.map-legend-item').forEach(button => {
        button.addEventListener('click', () => {
          const category = decodeURIComponent(button.dataset.categoryKey || '');
          if (activeCategories.has(category)) activeCategories.delete(category);
          else activeCategories.add(category);
          updateLayers();
          renderLegend();
        });
      });
      legendNode.querySelectorAll('[data-action]').forEach(button => {
        button.addEventListener('click', () => {
          const action = button.dataset.action;
          activeCategories.clear();
          if (action === 'all') categories.forEach(item => activeCategories.add(item.key));
          if (action === 'top') categories.slice(0, 10).forEach(item => activeCategories.add(item.key));
          updateLayers();
          renderLegend();
        });
      });
      filterLegendItems();
    };

    const modeControl = L.control({ position: 'topleft' });
    modeControl.onAdd = () => {
      const node = L.DomUtil.create('div', 'map-mode-control');
      node.innerHTML = `
        <button type="button" class="map-mode-button active" data-mode="points" title="Show category-coloured coordinates"><i class="fa-solid fa-location-dot"></i><span>Points</span></button>
        <button type="button" class="map-mode-button" data-mode="heat" title="Show incident density"><i class="fa-solid fa-fire-flame-curved"></i><span>Heat</span></button>
        <button type="button" class="map-mode-button" data-mode="both" title="Show points and density"><i class="fa-solid fa-layer-group"></i><span>Both</span></button>`;
      L.DomEvent.disableClickPropagation(node);
      node.querySelectorAll('.map-mode-button').forEach(button => {
        button.addEventListener('click', () => {
          layerMode = button.dataset.mode || 'points';
          applyLayerMode();
        });
      });
      return node;
    };
    modeControl.addTo(map);

    const fitVisible = () => {
      const records = currentRecords();
      if (!records.length) return;
      const bounds = L.latLngBounds(records.map(record => record.marker.getLatLng()));
      map.fitBounds(bounds.pad(.08), { maxZoom: 13 });
    };

    const actionControl = L.control({ position: 'topleft' });
    actionControl.onAdd = () => {
      const node = L.DomUtil.create('div', 'map-action-stack');
      const fitButton = L.DomUtil.create('button', 'map-action-button', node);
      fitButton.type = 'button';
      fitButton.title = 'Fit map to visible category coordinates';
      fitButton.innerHTML = '<i class="fa-solid fa-arrows-to-circle"></i>';
      const fullButton = L.DomUtil.create('button', 'map-action-button', node);
      fullButton.type = 'button';
      fullButton.title = 'Open full-screen map';
      fullButton.innerHTML = '<i class="fa-solid fa-expand"></i>';
      L.DomEvent.disableClickPropagation(node);
      fitButton.addEventListener('click', fitVisible);
      fullButton.addEventListener('click', () => {
        const enabled = mapElement.classList.toggle('map-fullscreen');
        document.body.classList.toggle('map-fullscreen-open', enabled);
        fullButton.innerHTML = enabled ? '<i class="fa-solid fa-compress"></i>' : '<i class="fa-solid fa-expand"></i>';
        fullButton.title = enabled ? 'Exit full-screen map' : 'Open full-screen map';
        setTimeout(() => map.invalidateSize(), 120);
      });
      return node;
    };
    actionControl.addTo(map);

    mapElement.addEventListener('click', event => {
      const button = event.target.closest('.copy-coordinate');
      if (!button) return;
      const coordinate = button.dataset.coordinate || '';
      if (!coordinate) return;
      const finish = () => {
        const original = button.textContent;
        button.textContent = 'Copied';
        setTimeout(() => { button.textContent = original; }, 1200);
      };
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        navigator.clipboard.writeText(coordinate).then(finish).catch(() => window.prompt('Copy coordinates:', coordinate));
      } else {
        window.prompt('Copy coordinates:', coordinate);
      }
    });

    updateLayers();
    renderLegend();
    fitVisible();

    const streamStatus = document.getElementById('streamStatus');
    const streamDot = document.getElementById('streamDot');
    if (streamStatus && streamDot) {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      let socket = null;
      let reconnectTimer = null;
      let reconnectAttempts = 0;
      let closingPage = false;

      const updateStreamStatus = (state, text) => {
        streamDot.className = `stream-dot ${state}`;
        streamStatus.textContent = text;
      };

      const removeExistingRecord = identity => {
        const existing = markerRecordsByIdentity.get(identity);
        if (!existing) return false;
        const index = markerRecords.indexOf(existing);
        if (index >= 0) markerRecords.splice(index, 1);
        markerRecordsByIdentity.delete(identity);
        return true;
      };

      const renderLiveIncident = (item, identity) => {
        const body = document.getElementById('liveIncidentRows');
        if (!body) return;
        body.querySelectorAll('tr .empty-state').forEach(cell => cell.closest('tr')?.remove());
        const oldRow = [...body.children].find(row => row.dataset.incidentIdentity === identity);
        if (oldRow) oldRow.remove();
        const row = document.createElement('tr');
        row.dataset.incidentIdentity = identity;
        row.innerHTML = `<td>${item.reported_at ? new Date(item.reported_at).toLocaleString() : '—'}</td><td><span class="source-badge source-${String(item.source_type || '').toLowerCase()}">${escapeHtml(item.source_type || 'Incident')}</span></td><td>${escapeHtml(item.event_id || '—')}</td><td>${escapeHtml(categoryFor(item))}</td><td>${escapeHtml(item.incident_location || item.police_station || '—')}</td><td>${escapeHtml(item.event_status || '—')}</td>`;
        body.prepend(row);
        while (body.children.length > 12) body.lastElementChild.remove();
      };

      const handleIncident = item => {
        if (!item) return;
        item.map_category = categoryFor(item);
        const identity = incidentIdentity(item);
        const isNewIncident = !seenIncidentIdentities.has(identity);
        seenIncidentIdentities.add(identity);
        const wasMapped = removeExistingRecord(identity);
        const record = createMarkerRecord(item);
        if (record) {
          markerRecords.unshift(record);
          markerRecordsByIdentity.set(identity, record);
          activeCategories.add(record.selectionKey);
        }

        if (isNewIncident) {
          metadata.filtered_total = Number(metadata.filtered_total || markerRecords.length - (record ? 1 : 0)) + 1;
          const totalKpi = document.getElementById('totalKpi');
          const streamKpi = document.getElementById('streamKpi');
          if (totalKpi) totalKpi.textContent = (Number(String(totalKpi.textContent || '0').replace(/,/g, '')) + 1).toLocaleString();
          if (streamKpi && item.origin === 'STREAM') streamKpi.textContent = (Number(String(streamKpi.textContent || '0').replace(/,/g, '')) + 1).toLocaleString();
        }
        if (!wasMapped && record) {
          metadata.mapped_total = Number(metadata.mapped_total || markerRecords.length - 1) + 1;
        } else if (wasMapped && !record) {
          metadata.mapped_total = Math.max(Number(metadata.mapped_total || markerRecords.length + 1) - 1, 0);
        }

        updateLayers();
        renderLegend();
        renderLiveIncident(item, identity);
      };

      const removeIncidentFromView = item => {
        const identity = incidentIdentity(item);
        if (!seenIncidentIdentities.has(identity)) return;
        seenIncidentIdentities.delete(identity);
        const wasMapped = removeExistingRecord(identity);
        const body = document.getElementById('liveIncidentRows');
        const row = [...(body?.children || [])].find(node => node.dataset.incidentIdentity === identity);
        row?.remove();
        metadata.filtered_total = Math.max(Number(metadata.filtered_total || 1) - 1, 0);
        if (wasMapped) metadata.mapped_total = Math.max(Number(metadata.mapped_total || 1) - 1, 0);

        const totalKpi = document.getElementById('totalKpi');
        const streamKpi = document.getElementById('streamKpi');
        if (totalKpi) totalKpi.textContent = Math.max(Number(String(totalKpi.textContent || '0').replace(/,/g, '')) - 1, 0).toLocaleString();
        if (streamKpi && item.origin === 'STREAM') {
          streamKpi.textContent = Math.max(Number(String(streamKpi.textContent || '0').replace(/,/g, '')) - 1, 0).toLocaleString();
        }
        updateLayers();
        renderLegend();
      };

      const scheduleReconnect = () => {
        if (closingPage || reconnectTimer) return;
        reconnectAttempts += 1;
        const delay = Math.min(30000, 1000 * (2 ** Math.min(reconnectAttempts - 1, 5)));
        updateStreamStatus('offline', `Live stream reconnecting in ${Math.ceil(delay / 1000)}s`);
        reconnectTimer = window.setTimeout(() => {
          reconnectTimer = null;
          connectStream();
        }, delay);
      };

      const connectStream = () => {
        if (closingPage) return;
        updateStreamStatus('offline', reconnectAttempts ? 'Reconnecting live stream…' : 'Connecting live stream…');
        socket = new WebSocket(`${protocol}://${window.location.host}/ws/incidents/`);
        socket.onopen = () => {
          reconnectAttempts = 0;
          updateStreamStatus('online', 'Live stream connected');
        };
        socket.onclose = () => {
          socket = null;
          scheduleReconnect();
        };
        socket.onerror = () => updateStreamStatus('offline', 'Live stream connection error');
        socket.onmessage = event => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'incident.created') {
              const incident = message.incident || {};
              if (matchesLiveFilters(incident)) handleIncident(incident);
              else removeIncidentFromView(incident);
            }
          } catch (error) {
            console.warn('Ignored invalid live incident payload.', error);
          }
        };
      };

      window.addEventListener('beforeunload', () => {
        closingPage = true;
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
      });
      connectStream();
    }
  };

  if (mapElement) {
    const embeddedPoints = rows(payload.map_points);
    if (embeddedPoints.length) {
      initializeIncidentMap({ points: embeddedPoints, metadata: payload.map_metadata || {} });
    } else if (mapElement.dataset.mapUrl) {
      mapElement.classList.add('map-loading');
      fetch(mapElement.dataset.mapUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => {
          if (!response.ok) throw new Error(`Map data request failed (${response.status})`);
          return response.json();
        })
        .then(data => initializeIncidentMap(data))
        .catch(error => {
          mapElement.innerHTML = `<div class="map-load-error"><i class="fa-solid fa-triangle-exclamation"></i><span>${escapeHtml(error.message)}</span></div>`;
        })
        .finally(() => mapElement.classList.remove('map-loading'));
    } else {
      initializeIncidentMap({ points: [], metadata: {} });
    }
  }

})();
