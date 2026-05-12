let cachedGeoJson = null;
let activityFilter = null;

const clearBtn = document.getElementById("clearFilters");

clearBtn.addEventListener("click", () => {
  activityFilter = null;
  document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });
  applyFilters();
});

window.filterByActivity = function(actName) {
  activityFilter = actName;
  document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
    cb.checked = false;
  });
  applyFilters();
};


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

        const filteredEntities = activityFilter !== null
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
  cachedGeoJson = schoolsData;
  applyWithData(schoolsData);
}


document.querySelectorAll('#filters input[type="checkbox"]').forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    activityFilter = null; // checkbox interaction clears activity filter
    applyFilters();
  });
});

applyFilters();
