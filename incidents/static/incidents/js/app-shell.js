(() => {
  const sidebar = document.getElementById('appSidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const openButton = document.getElementById('sidebarToggle');
  const closeButton = document.getElementById('sidebarClose');
  const collapseButton = document.getElementById('sidebarCollapse');
  if (!sidebar || !overlay) return;

  const open = () => {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.classList.add('sidebar-open');
  };
  const close = () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.classList.remove('sidebar-open');
  };

  const setCollapsed = collapsed => {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    localStorage.setItem('incident-sidebar-collapsed', collapsed ? '1' : '0');
    if (collapseButton) {
      collapseButton.innerHTML = collapsed
        ? '<i class="fa-solid fa-angles-right"></i>'
        : '<i class="fa-solid fa-angles-left"></i>';
    }
  };

  if (window.innerWidth >= 992) {
    setCollapsed(localStorage.getItem('incident-sidebar-collapsed') === '1');
  }
  collapseButton?.addEventListener('click', () => setCollapsed(!document.body.classList.contains('sidebar-collapsed')));

  document.querySelectorAll('.sidebar-group').forEach(group => {
    const key = group.dataset.sidebarGroup;
    const button = group.querySelector('.sidebar-group-toggle');
    const hasActive = Boolean(group.querySelector('.sidebar-link.active'));
    const stored = localStorage.getItem(`incident-sidebar-group-${key}`);
    const collapsed = stored === 'closed' && !hasActive;
    group.classList.toggle('group-closed', collapsed);
    button?.addEventListener('click', () => {
      const next = !group.classList.contains('group-closed');
      group.classList.toggle('group-closed', next);
      localStorage.setItem(`incident-sidebar-group-${key}`, next ? 'closed' : 'open');
    });
  });

  openButton?.addEventListener('click', open);
  closeButton?.addEventListener('click', close);
  overlay.addEventListener('click', close);
  window.addEventListener('resize', () => {
    if (window.innerWidth >= 992) close();
  });
})();
