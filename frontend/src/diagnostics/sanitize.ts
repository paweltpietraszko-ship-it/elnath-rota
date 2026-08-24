// T021c section 3.5: strip identifiers and query strings from request
// paths before they ever enter the diagnostic buffer. Only the static
// route template survives.

const ID_SEGMENT = /^([0-9a-fA-F-]{8,}|R-[A-Z0-9-]{4,}|[0-9]{4,})$/;

export function sanitizeEndpoint(path: string): string {
  const withoutQuery = path.split("?")[0];
  return withoutQuery
    .split("/")
    .map((segment) => (segment && ID_SEGMENT.test(segment) ? ":id" : segment))
    .join("/");
}
