// Resolve the theme before first paint. Keep the key in sync with theme/index.tsx.
(function () {
  try {
    var stored = localStorage.getItem('app-theme');
    var dark =
      stored === 'dark' ||
      ((stored === 'system' || !stored) &&
        window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.add(dark ? 'dark' : 'light');
  } catch (_error) {
    document.documentElement.classList.add('light');
  }
})();
