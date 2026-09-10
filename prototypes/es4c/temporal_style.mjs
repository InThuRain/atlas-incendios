// Escala temporal común del mapa nacional. Reproduce la paleta del visor GVA
// histórico, pero hace explícito el dominio que acompaña al periodo solicitado.

export const TEMPORAL_OLD_RGB = Object.freeze([44, 123, 182]);
export const TEMPORAL_RECENT_RGB = Object.freeze([240, 82, 46]);
export const GEOMETRY_TEMPORAL_COVERAGE = Object.freeze({ from: 1985, to: 2026 });

export function rgbString(values) {
  return `rgb(${values.join(",")})`;
}

export const TEMPORAL_OLD_COLOR = rgbString(TEMPORAL_OLD_RGB);
export const TEMPORAL_RECENT_COLOR = rgbString(TEMPORAL_RECENT_RGB);

function validYear(value) {
  return Number.isInteger(Number(value));
}

/**
 * El dominio es el tramo del periodo solicitado que puede contener polígonos
 * nacionales. No depende de features cargadas ni de filtros analíticos:
 * aplicar área/GIF/causa no cambia el significado de un color ya visible.
 */
export function temporalDomain(from, to, coverage = GEOMETRY_TEMPORAL_COVERAGE) {
  if (!validYear(from) || !validYear(to) || Number(from) > Number(to)) return null;
  const start = Math.max(Number(from), Number(coverage.from));
  const end = Math.min(Number(to), Number(coverage.to));
  return start <= end ? { from: start, to: end } : null;
}

/** Replica la interpolación lineal RGB con redondeo del GVA Leaflet. */
export function temporalColor(year, domain) {
  if (!domain || !validYear(year)) return TEMPORAL_OLD_COLOR;
  const denominator = Math.max(1, Number(domain.to) - Number(domain.from));
  const ratio = Math.max(0, Math.min(1, (Number(year) - Number(domain.from)) / denominator));
  return rgbString(TEMPORAL_OLD_RGB.map((value, index) => Math.round(
    value + (TEMPORAL_RECENT_RGB[index] - value) * ratio,
  )));
}

/** Expresión MapLibre equivalente al color por año; el caso de un año es azul. */
export function temporalColorExpression(domain, property = "year") {
  if (!domain || Number(domain.from) === Number(domain.to)) return TEMPORAL_OLD_COLOR;
  return [
    "interpolate", ["linear"], ["to-number", ["get", property]],
    Number(domain.from), TEMPORAL_OLD_COLOR,
    Number(domain.to), TEMPORAL_RECENT_COLOR,
  ];
}

export function temporalVisualState(from, to) {
  const domain = temporalDomain(from, to);
  return {
    domain,
    palette: { old: TEMPORAL_OLD_COLOR, recent: TEMPORAL_RECENT_COLOR },
    single_year: Boolean(domain && domain.from === domain.to),
    expression: temporalColorExpression(domain),
  };
}
