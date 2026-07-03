const TYPE_META = {
  venta: { label: 'Venta', color: '#12332e' },
  alquiler: { label: 'Alquiler', color: '#1e6fb8' },
  agencia: { label: 'Sara Álvarez', color: '#c2572a' }
};

const SOURCE_COLORS = {
  Idealista: '#b8c400',
  Fotocasa: '#0046fe',
  Wallapop: '#13c1ac',
  Milanuncios: '#f0524c',
  'Sara Álvarez Inmobiliaria': '#c2572a',
  'Inmobiliaria Freire': '#7a2b3a'
};

const state = {
  filter: 'todos',
  selectedId: null,
  showPricePins: true,
  properties: [],
  filteredCount: 0,
  totalCount: 0
};

const filtersEl = document.getElementById('filters');
const countEl = document.getElementById('count-pill');
const propertyCardEl = document.getElementById('property-card');
const radarListEl = document.getElementById('radar-list');
const togglePinsButton = document.getElementById('toggle-pins');
const toggleLabel = document.getElementById('toggle-label');
const runVigilanteButton = document.getElementById('run-vigilante');
const vigilanteStatusEl = document.getElementById('vigilante-status');

let map;
let markerLayer;

function formatPrice(item) {
  if (item.price == null) return 'Consultar';
  if (item.type === 'alquiler') return `${item.price} €/mes`;
  return `${Number(item.price).toLocaleString('es-ES')} €`;
}

function normalizeProperty(item) {
  return {
    id: item.id,
    source: item.source,
    url: item.sourceUrl || item.url || '#',
    type: item.type,
    price: item.price,
    lat: item.lat,
    lng: item.lng,
    title: item.title,
    address: item.address,
    specs: item.rooms && item.m2 ? `${item.rooms} hab · ${item.m2} m²` : item.specs || 'Consulta',
    ptype: item.ptype || 'Propiedad',
    orient: item.orientation || 'Consultar',
    owner: item.ownerKind === 'particular' ? 'Particular' : 'Agencia',
    daysAgo: item.daysAgo ?? 0,
    photo: item.photoUrl || `https://picsum.photos/seed/galicia${item.id}/640/400`,
    locationPrecision: item.locationPrecision || 'exact'
  };
}

function getFilteredProperties() {
  if (state.filter === 'todos') return state.properties;
  return state.properties.filter(p => p.type === state.filter);
}

async function loadProperties() {
  try {
    const url = `./data/properties.json`;
    const response = await fetch(url);
    const data = await response.json();
    state.properties = (data.properties || []).map(normalizeProperty);
    state.filteredCount = data.filteredCount || state.properties.length;
    state.totalCount = data.totalCount || state.properties.length;
    render();
  } catch (error) {
    try {
      const response = await fetch(`/api/properties?type=${state.filter}&limit=400`);
      const data = await response.json();
      state.properties = (data.properties || []).map(normalizeProperty);
      state.filteredCount = data.filteredCount || state.properties.length;
      state.totalCount = data.totalCount || state.properties.length;
      render();
    } catch (fallbackError) {
      console.error('No se pudieron cargar las propiedades', fallbackError);
    }
  }
}

function setStatus(message) {
  if (vigilanteStatusEl) {
    vigilanteStatusEl.textContent = message;
  }
}

async function runVigilante() {
  if (!runVigilanteButton) return;
  runVigilanteButton.disabled = true;
  runVigilanteButton.textContent = 'Ejecutando...';
  setStatus('Ejecutando vigilante...');
  try {
    const response = await fetch('/api/vigilante/run', { method: 'POST' });
    const data = await response.json();
    setStatus(data.message || 'Vigilante ejecutado.');
    await loadProperties();
  } catch (error) {
    setStatus('No se pudo ejecutar el vigilante.');
  } finally {
    runVigilanteButton.disabled = false;
    runVigilanteButton.textContent = 'Ejecutar vigilante ahora';
  }
}

function renderFilters() {
  const filters = [
    { key: 'todos', label: 'Todos' },
    { key: 'venta', label: 'Venta' },
    { key: 'alquiler', label: 'Alquiler' },
    { key: 'agencia', label: 'Sara Álvarez' }
  ];

  filtersEl.innerHTML = filters.map(filter => {
    const active = state.filter === filter.key;
    return `<button class="filter-pill ${active ? 'active' : ''}" data-filter="${filter.key}">${filter.label}</button>`;
  }).join('');

  filtersEl.querySelectorAll('button').forEach(button => {
    button.addEventListener('click', () => {
      state.filter = button.dataset.filter;
      state.selectedId = null;
      loadProperties();
    });
  });
}

function renderCount() {
  const visibleCount = state.filter === 'todos' ? state.totalCount : state.filteredCount;
  countEl.textContent = `${visibleCount} propiedades`;
}

function renderPropertyCard() {
  const selected = state.properties.find(p => p.id === state.selectedId);
  if (!selected) {
    propertyCardEl.innerHTML = '';
    return;
  }

  const typeMeta = TYPE_META[selected.type] || TYPE_META.venta;
  const sourceColor = SOURCE_COLORS[selected.source] || '#888';
  propertyCardEl.innerHTML = `
    <div class="card">
      <div class="card-image" style="background-image:url('${selected.photo}')">
        <button class="close-btn" type="button" aria-label="Cerrar ficha">✕</button>
        <div class="card-badge" style="background:${typeMeta.color}">${typeMeta.label}</div>
      </div>
      <div class="card-body">
        <div class="card-top">
          <div class="price">${formatPrice(selected)}</div>
          <div class="specs">${selected.specs}</div>
        </div>
        <div class="title">${selected.title}</div>
        <div class="address">${selected.address}</div>
        <div class="chips">
          <span class="chip">🏠 ${selected.ptype}</span>
          <span class="chip">🧭 Orientación: ${selected.orient}</span>
        </div>
        <a class="external-link" href="${selected.url}" target="_blank" rel="noopener noreferrer">
          <span class="source-pill"><span class="source-dot" style="background:${sourceColor}"></span> Ver en ${selected.source}</span>
          <span>→</span>
        </a>
      </div>
    </div>`;

  propertyCardEl.querySelector('.close-btn').addEventListener('click', () => {
    state.selectedId = null;
    render();
  });
}

function renderRadar() {
  const radarItems = state.properties
    .filter(p => p.owner === 'Particular')
    .sort((a, b) => a.daysAgo - b.daysAgo)
    .slice(0, 15);

  radarListEl.innerHTML = radarItems.map(item => `
    <button class="radar-item ${item.id === state.selectedId ? 'active' : ''}" data-id="${item.id}" type="button">
      <div class="radar-meta">
        <span class="radar-when">${item.daysAgo === 0 ? 'Nuevo hoy' : item.daysAgo === 1 ? 'Ayer' : `Hace ${item.daysAgo} días`}</span>
        <span class="radar-source">${item.source}</span>
      </div>
      <div class="radar-title-text">${item.title}</div>
      <div class="radar-meta">
        <span class="radar-address">${item.address}</span>
        <span class="radar-price">${formatPrice(item)}</span>
      </div>
    </button>
  `).join('');

  radarListEl.querySelectorAll('.radar-item').forEach(button => {
    button.addEventListener('click', () => {
      state.selectedId = Number(button.dataset.id);
      const selected = state.properties.find(p => p.id === state.selectedId);
      if (selected && map) {
        map.setView([selected.lat, selected.lng], 13, { animate: true });
      }
      render();
    });
  });
}

function createMarkerIcon(item) {
  const selected = item.id === state.selectedId;
  const baseColor = item.type === 'agencia' ? TYPE_META.agencia.color : TYPE_META[item.type]?.color || '#12332e';
  const background = selected ? '#111' : baseColor;
  const html = state.showPricePins
    ? `<div class="price-pin" style="background:${background}; color:#fff; font-size:12px; font-weight:700; padding:4px 9px; border-radius:999px; white-space:nowrap;">${formatPrice(item)}</div>`
    : `<div class="price-pin" style="width:16px;height:16px;border-radius:50%;background:${background};border:3px solid #fff;"></div>`;
  return L.divIcon({ html, className: '', iconSize: state.showPricePins ? [60, 24] : [16, 16], iconAnchor: state.showPricePins ? [35, 13] : [11, 11] });
}

function renderMarkers() {
  if (!markerLayer) return;
  markerLayer.clearLayers();
  getFilteredProperties().forEach(item => {
    const marker = L.marker([item.lat, item.lng], { icon: createMarkerIcon(item) });
    marker.on('click', () => {
      state.selectedId = item.id;
      if (map) {
        map.panTo([item.lat, item.lng], { animate: true });
      }
      render();
    });
    markerLayer.addLayer(marker);
  });
}

function initMap() {
  map = L.map('map', { zoomControl: true }).setView([42.4318, -8.6446], 12);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19
  }).addTo(map);
  markerLayer = L.layerGroup().addTo(map);
  renderMarkers();
  map.invalidateSize();
}

function render() {
  renderFilters();
  renderCount();
  renderPropertyCard();
  renderRadar();
  renderMarkers();
  if (map) map.invalidateSize();
}

togglePinsButton.addEventListener('click', () => {
  state.showPricePins = !state.showPricePins;
  togglePinsButton.textContent = state.showPricePins ? 'Mostrar precio' : 'Solo color';
  toggleLabel.textContent = state.showPricePins ? 'Pines con precio' : 'Puntos de color';
  renderMarkers();
});

if (runVigilanteButton) {
  runVigilanteButton.addEventListener('click', runVigilante);
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  render();
  loadProperties();
  setInterval(loadProperties, 60000);
});

window.addEventListener('resize', () => {
  if (map) map.invalidateSize();
});
