(() => {
  'use strict';

  const dataNode = document.getElementById('analytics-data');
  const mapElement = document.getElementById('categoryLayerMap');
  if (!dataNode) return;

  let payload = {};
  try {
    payload = JSON.parse(dataNode.textContent || '{}');
  } catch (error) {
    console.error('Unable to read GIS map report payload.', error);
    return;
  }

  const colors = window.IncidentCategoryColors || {
    keyFor: value => String(value || 'Uncategorised').trim().toUpperCase(),
    colorFor: () => '#2563eb',
  };
  const layersByName = new Map(
    (Array.isArray(payload.category_layers) ? payload.category_layers : [])
      .map(layer => [String(layer.category || ''), layer]),
  );

  const escapeHtml = value => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const categoryColor = (category, item = null) => (
    item?.category_colour
    || layersByName.get(String(category || ''))?.category_colour
    || colors.colorFor(category)
  );
  const categoryFor = item => String(
    item?.map_category || item?.category || item?.sub_category || 'Uncategorised',
  ).trim() || 'Uncategorised';
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

  document.querySelectorAll('.category-layer-swatch[data-category]').forEach(node => {
    node.style.background = categoryColor(node.dataset.category || 'Uncategorised');
  });

  const coverage = payload.category_coverage || {};
  const coverageCanvas = document.getElementById('mappedCategoryChart');
  if (coverageCanvas && typeof Chart !== 'undefined') {
    new Chart(coverageCanvas, {
      type: 'bar',
      data: {
        labels: coverage.labels || [],
        datasets: [
          {
            label: 'Mapped',
            data: coverage.mapped || [],
            backgroundColor: '#247a55',
            borderRadius: 5,
            borderSkipped: false,
          },
          {
            label: 'Unmapped / invalid',
            data: coverage.unmapped || [],
            backgroundColor: '#d69a2d',
            borderRadius: 5,
            borderSkipped: false,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12 } },
          tooltip: {
            callbacks: {
              footer: items => {
                const total = items.reduce((sum, item) => sum + Number(item.raw || 0), 0);
                const mappedItem = items.find(item => item.dataset.label === 'Mapped');
                const mapped = Number(mappedItem?.raw || 0);
                return total ? `Coordinate coverage: ${((mapped / total) * 100).toFixed(1)}%` : '';
              },
            },
          },
        },
        scales: {
          x: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
          y: { stacked: true, grid: { display: false } },
        },
      },
    });
  }

  const search = document.getElementById('categoryAtlasSearch');
  if (search) {
    search.addEventListener('input', event => {
      const needle = String(event.target.value || '').trim().toLowerCase();
      document.querySelectorAll('#categoryAtlasTable tbody tr[data-category-row]').forEach(row => {
        row.hidden = Boolean(needle && !String(row.dataset.categoryRow || '').includes(needle));
      });
    });
  }

  if (!mapElement || typeof L === 'undefined') return;

  const cleanMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 20,
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  });
  const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  });

  const categoryMap = L.map(mapElement, {
    preferCanvas: true,
    layers: [cleanMap],
    zoomControl: true,
    minZoom: 6,
  }).setView([1.3733, 32.2903], 7);
  L.control.layers({ 'Clean administrative map': cleanMap, 'Street map': streetMap }, {}, {
    collapsed: true,
    position: 'topright',
  }).addTo(categoryMap);

  let activeColor = '#2563eb';
  const clusterIcon = cluster => {
    const total = cluster.getChildCount();
    const size = total >= 1000 ? 'xl' : total >= 250 ? 'lg' : total >= 50 ? 'md' : 'sm';
    return L.divIcon({
      html: `<div class="category-cluster-ring" style="background:conic-gradient(${activeColor} 0 100%)"><span>${total.toLocaleString()}</span></div>`,
      className: `incident-cluster category-cluster incident-cluster-${size}`,
      iconSize: L.point(50, 50),
    });
  };
  const categoryCluster = typeof L.markerClusterGroup === 'function'
    ? L.markerClusterGroup({
        chunkedLoading: true,
        chunkInterval: 150,
        chunkDelay: 25,
        showCoverageOnHover: false,
        maxClusterRadius: 46,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 16,
        iconCreateFunction: clusterIcon,
      })
    : L.layerGroup();
  const categoryHeat = typeof L.heatLayer === 'function'
    ? L.heatLayer([], {
        radius: 24,
        blur: 20,
        maxZoom: 13,
        minOpacity: .28,
        gradient: { .2: '#2563eb', .45: '#22c55e', .65: '#facc15', .82: '#f97316', 1: '#dc2626' },
      })
    : null;

  let layerMode = 'points';
  let currentBounds = [];
  const applyLayerMode = () => {
    if (categoryMap.hasLayer(categoryCluster)) categoryMap.removeLayer(categoryCluster);
    if (categoryHeat && categoryMap.hasLayer(categoryHeat)) categoryMap.removeLayer(categoryHeat);
    if (layerMode === 'points' || layerMode === 'both') categoryCluster.addTo(categoryMap);
    if (categoryHeat && (layerMode === 'heat' || layerMode === 'both')) categoryHeat.addTo(categoryMap);
    document.querySelectorAll('[data-category-mode]').forEach(button => {
      button.classList.toggle('active', button.dataset.categoryMode === layerMode);
    });
  };
  applyLayerMode();

  let legendNode = null;
  const categoryLegend = L.control({ position: 'bottomright' });
  categoryLegend.onAdd = () => {
    legendNode = L.DomUtil.create('div', 'single-category-map-legend');
    L.DomEvent.disableClickPropagation(legendNode);
    L.DomEvent.disableScrollPropagation(legendNode);
    return legendNode;
  };
  categoryLegend.addTo(categoryMap);

  const loading = document.getElementById('categoryMapLoading');
  const title = document.getElementById('categoryLayerTitle');
  const subtitle = document.getElementById('categoryLayerSubtitle');
  const focusColor = document.getElementById('categoryFocusColor');
  const summaryFields = {
    name: document.getElementById('focusCategoryName'),
    total: document.getElementById('focusTotal'),
    mapped: document.getElementById('focusMapped'),
    unmapped: document.getElementById('focusUnmapped'),
    coverage: document.getElementById('focusCoverage'),
    share: document.getElementById('focusShare'),
    loaded: document.getElementById('focusLoaded'),
    station: document.getElementById('focusStation'),
    stationCount: document.getElementById('focusStationCount'),
    latest: document.getElementById('focusLatest'),
    profile: document.getElementById('focusCategoryProfile'),
  };

  let requestSequence = 0;
  let requestController = null;

  const metadataFrom = button => ({
    category: button?.dataset.category || '',
    total: Number(button?.dataset.total || 0),
    mapped: Number(button?.dataset.mapped || 0),
    unmapped: Number(button?.dataset.unmapped || 0),
    coverage: Number(button?.dataset.coverage || 0),
    share: Number(button?.dataset.share || 0),
    station: button?.dataset.station || 'No mapped station',
    stationTotal: Number(button?.dataset.stationTotal || 0),
    latest: button?.dataset.latest || 'Not recorded',
  });

  const buttonForCategory = category => {
    const candidates = [...document.querySelectorAll('[data-category][data-mapped]')];
    return candidates.find(button => button.dataset.category === category)
      || candidates.find(button => colors.keyFor(button.dataset.category) === colors.keyFor(category))
      || null;
  };

  const updateSummary = (metadata, loadedCount = null) => {
    const color = categoryColor(metadata.category);
    if (title) title.textContent = metadata.category || 'Selected category map';
    if (subtitle) subtitle.textContent = metadata.category
      ? `Valid coordinates classified as ${metadata.category}. Switch between points, heat and combined modes.`
      : 'Choose a Category layer to display only its valid coordinates.';
    if (focusColor) focusColor.style.background = color;
    if (summaryFields.name) summaryFields.name.textContent = metadata.category || '—';
    if (summaryFields.name) summaryFields.name.style.borderLeftColor = color;
    if (summaryFields.total) summaryFields.total.textContent = metadata.total.toLocaleString();
    if (summaryFields.mapped) summaryFields.mapped.textContent = metadata.mapped.toLocaleString();
    if (summaryFields.unmapped) summaryFields.unmapped.textContent = metadata.unmapped.toLocaleString();
    if (summaryFields.coverage) summaryFields.coverage.textContent = `${metadata.coverage}%`;
    if (summaryFields.share) summaryFields.share.textContent = `${metadata.share}%`;
    if (summaryFields.loaded && loadedCount !== null) summaryFields.loaded.textContent = Number(loadedCount).toLocaleString();
    if (summaryFields.station) summaryFields.station.textContent = metadata.station || 'No mapped station';
    if (summaryFields.stationCount) summaryFields.stationCount.textContent = `${metadata.stationTotal.toLocaleString()} mapped incidents`;
    if (summaryFields.latest) summaryFields.latest.textContent = metadata.latest || 'Not recorded';
    if (summaryFields.profile) {
      summaryFields.profile.href = metadata.category
        ? `/analytics/categories/${encodeURIComponent(metadata.category)}/`
        : '#';
      summaryFields.profile.classList.toggle('disabled', !metadata.category);
    }
    if (legendNode) {
      legendNode.innerHTML = `<span style="background:${color}"></span><div><strong>${escapeHtml(metadata.category || 'No category')}</strong><small>${loadedCount === null ? 'Loading coordinates…' : `${Number(loadedCount).toLocaleString()} coordinates loaded`}</small></div>`;
    }
  };

  const markerPopup = (item, category, color) => {
    const latitude = Number(item.latitude);
    const longitude = Number(item.longitude);
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
    const coordinateText = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
    const source = [item.source_type, item.origin].filter(Boolean).join(' · ') || 'Not recorded';
    return `
      <div class="incident-popup">
        <div class="map-popup-category"><span class="map-popup-dot" style="background:${color}"></span>${escapeHtml(category)}</div>
        <div class="map-popup-status ${statusClass(status)}">${escapeHtml(status)}</div>
        ${subCategory}
        ${caseNature}
        <div class="map-popup-row"><i class="fa-solid fa-building-shield"></i><span><strong>Police station:</strong> ${station ? profileLink('stations', station, station) : 'Not recorded'}</span></div>
        <div class="map-popup-row"><i class="fa-solid fa-location-dot"></i><span><strong>Location:</strong> ${escapeHtml(location)}</span></div>
        <div class="map-popup-row"><i class="fa-regular fa-clock"></i><span><strong>Reported:</strong> ${escapeHtml(reported)}</span></div>
        <div class="map-popup-row"><i class="fa-solid fa-database"></i><span><strong>Data source:</strong> ${escapeHtml(source)}</span></div>
        <div class="map-popup-row"><i class="fa-solid fa-crosshairs"></i><span><strong>Coordinates:</strong> ${coordinateText}</span></div>
        <div class="map-popup-meta">
          <span class="map-popup-meta-item">Event ${escapeHtml(item.event_id || 'Not recorded')}</span>
          ${item.reporting_type ? `<span class="map-popup-meta-item">${escapeHtml(item.reporting_type)}</span>` : ''}
        </div>
        <div class="map-popup-actions">
          ${profileLink('categories', category, 'Category profile')}
          ${station ? profileLink('stations', station, 'Station profile') : ''}
          <button type="button" class="map-popup-button copy-coordinate" data-coordinate="${coordinateText}">Copy coordinates</button>
          <a class="map-popup-link" href="https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=17/${latitude}/${longitude}" target="_blank" rel="noopener">OpenStreetMap</a>
        </div>
      </div>`;
  };

  const fitVisible = () => {
    if (!currentBounds.length) {
      categoryMap.setView([1.3733, 32.2903], 7);
      return;
    }
    categoryMap.fitBounds(L.latLngBounds(currentBounds).pad(.08), { maxZoom: 13 });
  };

  const renderCategoryPoints = (category, response, metadata) => {
    categoryCluster.clearLayers();
    activeColor = categoryColor(category, response.points?.[0]);
    const points = Array.isArray(response.points) ? response.points : [];
    currentBounds = [];
    const heatPoints = [];
    points.forEach(item => {
      const latitude = Number(item.latitude);
      const longitude = Number(item.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
      const itemCategory = categoryFor(item);
      const color = categoryColor(itemCategory, item);
      const marker = L.circleMarker([latitude, longitude], {
        radius: 7,
        color: '#ffffff',
        fillColor: color,
        fillOpacity: .93,
        weight: 2,
      });
      marker.bindTooltip(`${escapeHtml(itemCategory)} · ${escapeHtml(item.police_station || item.incident_location || 'Mapped incident')}`, {
        direction: 'top',
        sticky: true,
        opacity: .94,
      });
      marker.bindPopup(markerPopup(item, itemCategory, color), { maxWidth: 390, minWidth: 300 });
      categoryCluster.addLayer(marker);
      currentBounds.push([latitude, longitude]);
      heatPoints.push([latitude, longitude, 1]);
    });
    if (categoryHeat && typeof categoryHeat.setLatLngs === 'function') categoryHeat.setLatLngs(heatPoints);
    applyLayerMode();
    fitVisible();
    updateSummary(metadata, currentBounds.length);
  };

  const buildCategoryUrl = category => {
    const url = new URL(mapElement.dataset.baseUrl || '/api/v1/analytics/map-points/', window.location.origin);
    const baseQuery = new URLSearchParams(mapElement.dataset.baseQuery || '');
    baseQuery.forEach((value, key) => url.searchParams.set(key, value));
    url.searchParams.set('category', category);
    url.searchParams.set('limit', '50000');
    return url;
  };

  const selectCategory = async (category, metadataButton, scrollIntoView = false) => {
    if (!category) return;
    const button = metadataButton || buttonForCategory(category);
    const metadata = metadataFrom(button);
    metadata.category = category;

    document.querySelectorAll('.category-layer-button').forEach(node => {
      node.classList.toggle('active', node.dataset.category === category);
    });
    updateSummary(metadata, null);
    if (loading) loading.classList.add('show');
    mapElement.setAttribute('aria-busy', 'true');
    categoryCluster.clearLayers();
    if (categoryHeat && typeof categoryHeat.setLatLngs === 'function') categoryHeat.setLatLngs([]);

    if (scrollIntoView) {
      document.getElementById('category-layers')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    requestController?.abort();
    requestController = new AbortController();
    const sequence = ++requestSequence;
    try {
      const response = await fetch(buildCategoryUrl(category), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: requestController.signal,
      });
      if (!response.ok) throw new Error(`Map request failed (${response.status})`);
      const data = await response.json();
      if (sequence !== requestSequence) return;
      renderCategoryPoints(category, data, metadata);
      const currentUrl = new URL(window.location.href);
      currentUrl.searchParams.set('focus_category', category);
      window.history.replaceState({}, '', currentUrl);
    } catch (error) {
      if (error.name === 'AbortError' || sequence !== requestSequence) return;
      console.error(error);
      currentBounds = [];
      if (legendNode) legendNode.innerHTML = `<div><strong>${escapeHtml(category)}</strong><small>Unable to load coordinates. Retry the layer.</small></div>`;
      if (summaryFields.loaded) summaryFields.loaded.textContent = '0';
    } finally {
      if (sequence === requestSequence) {
        loading?.classList.remove('show');
        mapElement.removeAttribute('aria-busy');
      }
      setTimeout(() => categoryMap.invalidateSize(), 60);
    }
  };

  document.querySelectorAll('.category-layer-button').forEach(button => {
    button.addEventListener('click', () => selectCategory(button.dataset.category, button));
  });
  document.querySelectorAll('.open-category-layer').forEach(button => {
    button.addEventListener('click', () => selectCategory(button.dataset.category, button, true));
  });
  document.querySelectorAll('[data-category-mode]').forEach(button => {
    button.addEventListener('click', () => {
      layerMode = button.dataset.categoryMode || 'points';
      applyLayerMode();
    });
  });
  document.getElementById('fitCategoryMap')?.addEventListener('click', fitVisible);

  const fullscreenButton = document.getElementById('fullscreenCategoryMap');
  fullscreenButton?.addEventListener('click', () => {
    const card = mapElement.closest('.gis-map-card') || mapElement;
    const enabled = card.classList.toggle('focused-map-fullscreen');
    document.body.classList.toggle('map-fullscreen-open', enabled);
    fullscreenButton.classList.toggle('active', enabled);
    fullscreenButton.innerHTML = enabled
      ? '<i class="fa-solid fa-compress"></i><span>Exit</span>'
      : '<i class="fa-solid fa-expand"></i><span>Full</span>';
    fullscreenButton.title = enabled ? 'Exit full-screen Category map' : 'Open full-screen Category map';
    setTimeout(() => categoryMap.invalidateSize(), 120);
  });

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
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(coordinate).then(finish).catch(() => window.prompt('Copy coordinates:', coordinate));
    } else {
      window.prompt('Copy coordinates:', coordinate);
    }
  });

  window.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const card = mapElement.closest('.focused-map-fullscreen');
    if (!card) return;
    card.classList.remove('focused-map-fullscreen');
    document.body.classList.remove('map-fullscreen-open');
    if (fullscreenButton) {
      fullscreenButton.classList.remove('active');
      fullscreenButton.innerHTML = '<i class="fa-solid fa-expand"></i><span>Full</span>';
    }
    setTimeout(() => categoryMap.invalidateSize(), 120);
  });

  const initialCategory = mapElement.dataset.initialCategory || document.querySelector('.category-layer-button')?.dataset.category || '';
  if (initialCategory) {
    selectCategory(initialCategory, buttonForCategory(initialCategory));
  } else {
    updateSummary(metadataFrom(null), 0);
    loading?.classList.remove('show');
  }
})();
