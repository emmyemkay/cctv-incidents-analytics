(() => {
  const dataNode = document.getElementById('analytics-data');
  if (!dataNode || typeof Chart === 'undefined') return;
  const payload = JSON.parse(dataNode.textContent || '{}');
  const palette = ['#1867c0', '#6f42c1', '#15847a', '#f2a900', '#d64a3a', '#4d7c8a', '#8a5a44', '#4c956c'];
  const rows = value => Array.isArray(value) ? value : [];
  const values = (items, key) => rows(items).map(item => item[key]);
  const integerAxis = { beginAtZero: true, ticks: { precision: 0 } };
  const monthLabel = value => value ? new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short' }) : '';

  const chart = (id, config, filter) => {
    const element = document.getElementById(id);
    if (!element) return;
    if (filter) {
      config.options = config.options || {};
      config.options.onClick = (_, active, instance) => {
        if (!active.length) return;
        const label = instance.data.labels[active[0].index];
        const url = new URL(window.location.href);
        url.searchParams.set(filter, label);
        window.location.href = url.toString();
      };
    }
    new Chart(element, config);
  };

  const horizontalBar = (id, items, labelKey, dataKey = 'total', filter = null, color = '#6f42c1') => chart(id, {
    type: 'bar',
    data: { labels: values(items, labelKey), datasets: [{ data: values(items, dataKey), backgroundColor: color, borderRadius: 6 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
  }, filter);

  if (payload.area && payload.category && payload.time) {
    horizontalBar('areaTotalsChart', payload.area.by_area, 'police_station', 'total', 'station');
    const join = payload.area.category_area || {};
    chart('categoryAreaChart', {
      type: 'bar',
      data: { labels: rows(join.areas), datasets: rows(join.datasets).map((series, index) => ({ label: series.category, data: series.values, backgroundColor: palette[index % palette.length], borderRadius: 3 })) },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, scales: { x: { ...integerAxis, stacked: true }, y: { stacked: true, grid: { display: false } } } }
    });

    const pareto = rows(payload.area.station_pareto);
    chart('stationParetoChart', {
      data: {
        labels: values(pareto, 'police_station'),
        datasets: [
          { type: 'bar', label: 'Incidents', data: values(pareto, 'total'), backgroundColor: '#1867c0', borderRadius: 5, yAxisID: 'y' },
          { type: 'line', label: 'Cumulative share', data: values(pareto, 'cumulative_pct'), borderColor: '#d64a3a', backgroundColor: '#d64a3a', tension: .2, pointRadius: 2, yAxisID: 'y1' }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'bottom' } },
        scales: {
          y: { ...integerAxis, position: 'left' },
          y1: { beginAtZero: true, max: 100, position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: value => `${value}%` } },
          x: { grid: { display: false }, ticks: { maxRotation: 55, minRotation: 25 } }
        }
      }
    });

    const categoryTime = payload.category.category_time || {};
    chart('categoryTimeChart', {
      type: 'line',
      data: { labels: rows(categoryTime.months).map(monthLabel), datasets: rows(categoryTime.monthly_datasets).map((series, index) => ({ label: series.category, data: series.values, borderColor: palette[index % palette.length], backgroundColor: palette[index % palette.length], tension: .25, pointRadius: 1.5 })) },
      options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, scales: { y: integerAxis, x: { grid: { display: false } } } }
    });

    chart('hourChart', {
      type: 'line',
      data: { labels: values(payload.time.by_hour, 'label'), datasets: [{ data: values(payload.time.by_hour, 'total'), borderColor: '#15847a', backgroundColor: 'rgba(21,132,122,.13)', fill: true, tension: .25, pointRadius: 2 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: integerAxis, x: { grid: { display: false } } } }
    });

    chart('weekdayChart', {
      type: 'bar',
      data: { labels: values(payload.time.by_weekday, 'weekday'), datasets: [{ data: values(payload.time.by_weekday, 'total'), backgroundColor: '#f2a900', borderRadius: 7 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: integerAxis, x: { grid: { display: false } } } }
    });

    const heatmap = document.getElementById('timeHeatmap');
    if (heatmap && rows(payload.time.heatmap).length) {
      const maximum = Math.max(1, ...rows(payload.time.heatmap).flatMap(row => row.values));
      const header = `<div class="heatmap-row heatmap-header"><div></div>${rows(payload.time.hours).map(hour => `<div>${hour}</div>`).join('')}</div>`;
      const body = rows(payload.time.heatmap).map(row => `<div class="heatmap-row"><div class="heatmap-day">${row.weekday}</div>${row.values.map(value => `<div class="heatmap-cell" title="${row.weekday}: ${value} incidents" style="--heat:${Math.max(.06, value / maximum)}">${value || ''}</div>`).join('')}</div>`).join('');
      heatmap.innerHTML = header + body;
    }
  }

  if (payload.command && payload.dispatch && payload.status) {
    chart('commandTrendChart', {
      type: 'line',
      data: { labels: rows(payload.command.by_month).map(item => monthLabel(item.month)), datasets: [{ data: values(payload.command.by_month, 'total'), borderColor: '#1867c0', backgroundColor: 'rgba(24,103,192,.12)', fill: true, tension: .25, pointRadius: 2 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: integerAxis, x: { grid: { display: false } } } }
    });
    chart('operationsStatusChart', {
      type: 'doughnut',
      data: { labels: values(payload.status.by_status, 'event_status'), datasets: [{ data: values(payload.status.by_status, 'total'), backgroundColor: palette, borderColor: '#fff', borderWidth: 2 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '58%', plugins: { legend: { position: 'bottom' } } }
    }, 'status');
    horizontalBar('commandDestinationsChart', payload.command.destinations, 'police_station', 'total', 'station');
    horizontalBar('dispatchBranchChart', payload.dispatch.branch_totals, 'governing_branch', 'total', 'branch', '#1867c0');
    horizontalBar('stationClosureChart', payload.status.station_closure, 'police_station', 'closed_pct', 'station', '#15847a');

    chart('operationsAgingChart', {
      type: 'bar',
      data: { labels: values(payload.status.aging, 'label'), datasets: [{ data: values(payload.status.aging, 'total'), backgroundColor: ['#15847a', '#4d7c8a', '#f2a900', '#e76f51', '#d64a3a'], borderRadius: 7 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: integerAxis, y: { grid: { display: false } } } }
    });
  }
})();
