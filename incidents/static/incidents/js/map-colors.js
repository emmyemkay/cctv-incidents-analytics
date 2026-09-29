(() => {
  'use strict';

  const cache = new Map([['UNCATEGORISED', '#94a3b8']]);

  const stableHash = value => {
    let hash = 2166136261;
    for (const character of String(value)) {
      hash ^= character.codePointAt(0);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  };

  const keyFor = category => String(category || 'Uncategorised')
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/\s+\)/g, ')')
    .replace(/\(\s+/g, '(')
    .toUpperCase() || 'UNCATEGORISED';

  const colorFor = category => {
    const key = keyFor(category);
    if (cache.has(key)) return cache.get(key);

    const hash = stableHash(key);
    const hue = hash % 360;
    const saturation = 66 + ((hash >>> 8) % 20);
    const lightness = 38 + ((hash >>> 16) % 14);
    const color = `hsl(${hue} ${saturation}% ${lightness}%)`;
    cache.set(key, color);
    return color;
  };

  const descriptionFor = category => {
    const label = String(category || 'Uncategorised').trim() || 'Uncategorised';
    return `Mapped coordinates classified as ${label}.`;
  };

  window.IncidentCategoryColors = Object.freeze({ keyFor, colorFor, descriptionFor });
})();
