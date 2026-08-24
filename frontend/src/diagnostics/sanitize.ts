// T021c section 3.5: strip identifiers and query strings from request
// paths before they ever enter the diagnostic buffer. Only the static
// route template survives.
//
// R1-1 (round-1 audit): a hex/UUID-shaped check alone misses this app's
// prefixed IDs (SITE-<hex>, PROF-<hex>, R-EMP-MATRIX-<hex>, ...). None
// of this app's *static* route words (workspace, sites, employees,
// roster, matrix, target-hours, ...) contain a digit or a known ID
// prefix, so both checks below are safe, not just a partial patch.
const KNOWN_ID_PREFIXES = /^(SITE-|PROF-|R-)/;
const CONTAINS_DIGIT = /\d/;

function isIdSegment(segment: string): boolean {
  return KNOWN_ID_PREFIXES.test(segment) || CONTAINS_DIGIT.test(segment);
}

export function sanitizeEndpoint(path: string): string {
  const withoutQuery = path.split("?")[0];
  return withoutQuery
    .split("/")
    .map((segment) => (segment && isIdSegment(segment) ? ":id" : segment))
    .join("/");
}
