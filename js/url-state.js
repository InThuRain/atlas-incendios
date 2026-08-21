const HASH_VERSION = '1';

function finiteNumber(value) {
  if (value === null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function boundedInteger(value, minimum, maximum) {
  const number = finiteNumber(value);
  if (number === null) return null;
  const integer = Math.round(number);
  return integer >= minimum && integer <= maximum ? integer : null;
}

export function parseViewerHash(hash, {years, sourceIds, provinceIds}) {
  const source = String(hash || '').replace(/^#/, '');
  if (!source) return null;
  const params = new URLSearchParams(source);
  if (params.get('v') !== HASH_VERSION) return null;
  const result = {version: 1};
  const lat = finiteNumber(params.get('lat')), lng = finiteNumber(params.get('lng'));
  const zoom = boundedInteger(params.get('z'), 2, 19);
  if (lat !== null && lng !== null && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) result.center = {lat, lng};
  if (zoom !== null) result.zoom = zoom;
  const from = boundedInteger(params.get('from'), years.min, years.max);
  const to = boundedInteger(params.get('to'), years.min, years.max);
  if (from !== null && to !== null) { result.from = Math.min(from, to); result.to = Math.max(from, to); }
  const allowedSources = new Set(sourceIds);
  if (params.has('src')) {
    const rawSources = params.get('src'), requested = rawSources.split(',').filter(item => allowedSources.has(item));
    if (requested.length || rawSources === '') result.sources = requested;
  }
  if (provinceIds.includes(params.get('province'))) result.province = params.get('province');
  for (const key of ['municipality', 'cause', 'entity', 'geometry']) {
    const value = params.get(key);
    if (value && value.length <= 180) result[key] = value;
  }
  const minimumArea = finiteNumber(params.get('min_area'));
  if (minimumArea !== null && minimumArea >= 0) result.minimumArea = minimumArea;
  if (params.get('gif') === '1' || params.get('gif') === '0') result.gifOnly = params.get('gif') === '1';
  return result;
}

export function serializeViewerHash(view) {
  const params = new URLSearchParams();
  params.set('v', HASH_VERSION);
  if (view.center) { params.set('lat', Number(view.center.lat).toFixed(5)); params.set('lng', Number(view.center.lng).toFixed(5)); }
  if (view.zoom !== undefined) params.set('z', String(Math.round(view.zoom)));
  params.set('from', String(view.from)); params.set('to', String(view.to));
  params.set('src', [...view.sources].join(',')); params.set('province', view.province);
  if (view.municipality) params.set('municipality', view.municipality);
  params.set('min_area', String(view.minimumArea || 0)); params.set('gif', view.gifOnly ? '1' : '0');
  if (view.cause) params.set('cause', view.cause);
  if (view.entity) params.set('entity', view.entity);
  if (view.geometry) params.set('geometry', view.geometry);
  return `#${params.toString()}`;
}

export function permalinkFor(locationLike, hash) {
  return `${locationLike.origin}${locationLike.pathname}${hash}`;
}
