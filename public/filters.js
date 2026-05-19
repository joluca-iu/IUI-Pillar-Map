let cachedGeoJson = null;
let activityFilter = null;
let schoolFilter = null;
let partnerFilter = null; // Set of entity ID strings, or null

function clearAllFilters() {
  activityFilter = null;
  schoolFilter = null;
  partnerFilter = null;
  if (window.clearSchoolSearch) window.clearSchoolSearch();
}

window.setSchoolFilter = function(entityId) {
  clearAllFilters();
  schoolFilter = entityId || null;
  document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });
  applyFilters();
};

window.setPartnerFilter = function(partnerIds) {
  clearAllFilters();
  partnerFilter = partnerIds && partnerIds.length > 0
    ? new Set(partnerIds.map(String))
    : null;
  document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });
  applyFilters();
};

const clearBtn = document.getElementById("clearFilters");

clearBtn.addEventListener("click", () => {
  clearAllFilters();
  document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });
  applyFilters();
});


function check_filter_status() {
  const filterCheckBoxStatuses = {};

  document.querySelectorAll('#filters input.program').forEach(programCb => {
    const campus = programCb.dataset.campus ?? "";
    const campusClean = campus.replace(/\s+/g, '');
    const programClean = programCb.value.replace(/\s+/g, '');
    const key = `${campusClean}|${programClean}`;
    filterCheckBoxStatuses[key] = programCb.checked;
  });

  return filterCheckBoxStatuses;
}


function applyWithData(geo_json_data) {
  const filtered = {
    type: "FeatureCollection",
    features: geo_json_data.features
      .map(feature => {
        const entities = feature.properties?.entity ?? [];

        const filteredEntities = schoolFilter !== null
          // School filter mode: show only the selected entity by ID
          ? entities.filter(entity => entity.id === schoolFilter)
          : partnerFilter !== null
          // Partner filter mode: show only entities whose ID is in the partner set
          ? entities.filter(entity => partnerFilter.has(String(entity.id)))
          : activityFilter !== null
          // Activity filter mode: match against the raw activityName array (always populated)
          ? entities.filter(entity =>
              Array.isArray(entity.activityName) &&
              entity.activityName.includes(activityFilter)
            )
          // Normal mode: checkbox-based program filter
          : (() => {
              const filter_status = check_filter_status();
              return entities.filter(entity => {
                const portal = entity?.portal_name ?? "";
                const programs = entity?.programs ?? [];

                return Array.isArray(programs) && programs.some(p => {
                  const programClean = String(p).replace(/\s+/g, "");
                  const portalClean = String(portal).replace(/\s+/g, "");
                  const key = `${portalClean}|${programClean}`;
                  return filter_status[key] === true;
                });
              });
            })();

        return {
          ...feature,
          properties: { ...feature.properties, entity: filteredEntities }
        };
      })
      .filter(feature => (feature.properties?.entity ?? []).length > 0)
  };
  apply_markers(filtered);
}

function applyFilters() {
  if (cachedGeoJson) {
    applyWithData(cachedGeoJson);
    return;
  }
  fetch("site_data/schools.geojson")
    .then(res => res.json())
    .then(geo_json_data => {
      cachedGeoJson = geo_json_data;
      window.cachedGeoJson = geo_json_data;
      applyWithData(geo_json_data);
    })
    .catch(err => console.error("Error loading schools.geojson:", err));
}


document.querySelectorAll('#filters input[type="checkbox"]').forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    clearAllFilters();
    applyFilters();
  });
});

applyFilters();
