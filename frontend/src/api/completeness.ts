// Translates ContextCompleteness.missing reasons (raw English strings from
// rota/application/bootstrap.py::coordinator_context_completeness) into
// Polish. Every reachable pattern must be covered -- no anglicisms in UI
// (standing rule) and no raw backend text may reach the coordinator.
const PATTERNS: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/^coordinator '.+' is not active$/, () => "Koordynator jest nieaktywny."],
  [/^coordinator '.+' does not exist$/, () => "Koordynator nie istnieje w systemie."],
  [/^site '.+' is not active$/, () => "Obiekt jest nieaktywny."],
  [/^site profile '.+' is not active$/, () => "Profil zmianowy jest nieaktywny."],
  [
    /^site profile '.+' has no valid standard shift$/,
    () => "Profil zmianowy nie ma zdefiniowanej żadnej zmiany standardowej.",
  ],
  [/^site '.+' does not exist$/, () => "Obiekt nie istnieje w systemie."],
  [
    /^no active CoordinatorSiteAssociation for \(.+\)$/,
    () => "Brak aktywnego powiązania koordynatora z obiektem.",
  ],
  [
    /^site '.+' has no active LOCAL SiteMembership$/,
    () => "Obiekt nie ma przypisanej żadnej aktywnej obsady lokalnej.",
  ],
];

export function translateMissingReason(reason: string): string {
  for (const [pattern, translate] of PATTERNS) {
    const match = reason.match(pattern);
    if (match) return translate(match);
  }
  // Unknown shape: never show raw backend text to the coordinator.
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.warn("translateMissingReason: unrecognized completeness reason", reason);
  }
  return "Brakujący element konfiguracji.";
}
