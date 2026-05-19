(function () {
  let searchIndex = [];
  let indexBuilt = false;
  let activeResultIndex = -1;

  function buildIndex() {
    const geo = window.cachedGeoJson;
    if (!geo || indexBuilt) return;

    const seen = new Set();
    geo.features.forEach(feature => {
      (feature.properties?.entity ?? []).forEach(entity => {
        if (entity.id && entity.name && !seen.has(entity.id)) {
          seen.add(entity.id);
          searchIndex.push({ id: entity.id, name: entity.name, nameLower: entity.name.toLowerCase() });
        }
      });
    });
    searchIndex.sort((a, b) => a.nameLower.localeCompare(b.nameLower));
    indexBuilt = true;
  }

  function query(raw) {
    if (!raw || raw.trim() === '') return [];
    const q = raw.trim().toLowerCase();
    const starts = [];
    const contains = [];
    searchIndex.forEach(entry => {
      if (entry.nameLower.startsWith(q)) starts.push(entry);
      else if (entry.nameLower.includes(q)) contains.push(entry);
    });
    return [...starts, ...contains].slice(0, 20);
  }

  let inputEl, dropdownEl;

  function renderDropdown(results) {
    dropdownEl.innerHTML = '';
    if (!results.length) {
      dropdownEl.style.display = 'none';
      return;
    }
    results.forEach(entry => {
      const item = document.createElement('div');
      item.className = 'search-result-item';
      item.textContent = entry.name;
      item.dataset.entityId = entry.id;
      item.dataset.entityName = entry.name;
      item.addEventListener('mousedown', e => {
        e.preventDefault();
        selectEntity(entry.id, entry.name);
      });
      dropdownEl.appendChild(item);
    });
    activeResultIndex = -1;
    dropdownEl.style.display = 'block';
  }

  function highlightResult(index) {
    dropdownEl.querySelectorAll('.search-result-item').forEach((el, i) => {
      el.classList.toggle('search-result-active', i === index);
    });
  }

  function selectEntity(id, name) {
    inputEl.value = name;
    dropdownEl.style.display = 'none';
    activeResultIndex = -1;
    window.setSchoolFilter(id);
    window.openEntityPopup(id, name);
    const entry = window._markerRegistry?.[id];
    if (entry && window.map) {
      window.map.setView(entry.marker.getLatLng(), window.map.getZoom());
    }
  }

  window.clearSchoolSearch = function () {
    if (inputEl) inputEl.value = '';
    if (dropdownEl) dropdownEl.style.display = 'none';
    activeResultIndex = -1;
    indexBuilt = false;
    searchIndex = [];
  };

  document.addEventListener('DOMContentLoaded', () => {
    inputEl = document.getElementById('schoolSearchInput');
    dropdownEl = document.getElementById('schoolSearchDropdown');

    inputEl.addEventListener('input', () => {
      if (!indexBuilt) buildIndex();
      renderDropdown(query(inputEl.value));
    });

    inputEl.addEventListener('keydown', e => {
      const items = dropdownEl.querySelectorAll('.search-result-item');
      if (!items.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeResultIndex = Math.min(activeResultIndex + 1, items.length - 1);
        highlightResult(activeResultIndex);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeResultIndex = Math.max(activeResultIndex - 1, 0);
        highlightResult(activeResultIndex);
      } else if (e.key === 'Enter') {
        if (activeResultIndex >= 0 && items[activeResultIndex]) {
          const el = items[activeResultIndex];
          selectEntity(el.dataset.entityId, el.dataset.entityName);
        }
      } else if (e.key === 'Escape') {
        dropdownEl.style.display = 'none';
      }
    });

    inputEl.addEventListener('blur', () => {
      setTimeout(() => { dropdownEl.style.display = 'none'; }, 150);
    });

    inputEl.addEventListener('focus', () => {
      if (inputEl.value.trim()) {
        if (!indexBuilt) buildIndex();
        renderDropdown(query(inputEl.value));
      }
    });
  });
})();
