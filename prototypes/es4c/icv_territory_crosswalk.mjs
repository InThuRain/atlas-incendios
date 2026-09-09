/** Crosswalk documental de provincia para el snapshot ICV 1993--2024.
 *
 * Los valores son grafías observadas en `fires.json`, no una normalización
 * difusa.  Un valor que no esté documentado aquí permanece sin resolver: no
 * se adivina una provincia por mayúsculas, acentos, municipio o geometría.
 */

export const ICV_CCAA_ID = "ES:CCAA:10";

const rows = [
  ["ALICANTE", "alicante", "ES:PROV:03", "Alicante/Alacant"],
  ["Alicante/Alacant", "alicante", "ES:PROV:03", "Alicante/Alacant"],
  ["CASTELLON", "castellon", "ES:PROV:12", "Castellón/Castelló"],
  ["Castellon", "castellon", "ES:PROV:12", "Castellón/Castelló"],
  ["Castellón/Castelló", "castellon", "ES:PROV:12", "Castellón/Castelló"],
  ["VALENCIA", "valencia", "ES:PROV:46", "Valencia/València"],
  ["Valencia/València", "valencia", "ES:PROV:46", "Valencia/València"],
];

export const ICV_PROVINCE_CROSSWALK = Object.freeze(rows.reduce((crosswalk, [raw_value, province_key, territory_id, normalized_value]) => {
  crosswalk[raw_value] = Object.freeze({raw_value, province_key, territory_id, normalized_value, autonomous_community_id: ICV_CCAA_ID});
  return crosswalk;
}, {}));

/** Devuelve únicamente una equivalencia explícitamente documentada. */
export function resolveIcvProvince(rawValue) {
  return typeof rawValue === "string" ? ICV_PROVINCE_CROSSWALK[rawValue] || null : null;
}
