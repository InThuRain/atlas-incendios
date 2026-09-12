/** One gesture, one owner. Never rely on listener registration order. */
export function routeMapClick(event, {
  pointQueryActive = () => false, handlePointQuery = () => {},
  queryFireHits, handleFireHits, queryTerritory, handleTerritory, handleEmpty = () => {},
}) {
  if (pointQueryActive()) { handlePointQuery(event); return "point_query"; }
  const hits = queryFireHits(event.point);
  if (hits.length) { handleFireHits(hits, event); return "fire"; }
  const territory = queryTerritory(event.point);
  if (territory) { handleTerritory(territory, event); return "territory"; }
  handleEmpty(event);
  return "empty";
}
