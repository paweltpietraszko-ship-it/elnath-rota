# ROTA-T049 — usunięcie pola „Nazwa profilu zmianowego” z formularza nowego obiektu

STATUS: PROPOZYCJA DO WERYFIKACJI CC — ZERO KODU PRODUKTU — IMPLEMENTACJA
DOPIERO PO PASS PREIMPLEMENTATION AUDIT

BASE_MAIN_SHA: `3521b500621fdb8401827e0c73ce60a572eb3678`

Źródło: Paweł, dodając nowy obiekt, zobaczył wymagane pole „Nazwa profilu
zmianowego” z podpowiedzią „np. PROF-NORDPLAST-02” i nie wiedział, po co ono
jest. Sprawdzone w kodzie: to jest osobna nazwa własna dla wewnętrznego
`SiteProfile` — encji technicznej, zawsze tworzonej jeden-do-jednego z
nowym obiektem (`profile_id` to zawsze świeży losowy `PROF-<uuid>`, nigdy
wpisany przez koordynatora tekst), nigdy współdzielonej z innym obiektem
(sprawdzony cały kod — nie ma nigdzie opcji „wybierz istniejący profil”).
Ta nazwa nigdzie się już potem nie pokazuje koordynatorowi (żaden ekran jej
nie czyta poza jednorazowym zapisem przy tworzeniu). OWNER: usunąć pole.

## 1. Cel

Usunąć wymagane pole „Nazwa profilu zmianowego” z formularza tworzenia
nowego obiektu. Koordynator ma podać tylko nazwę obiektu — wewnętrzna nazwa
`SiteProfile` ma być wyprowadzona automatycznie z nazwy obiektu, bez pytania
o nią.

## 1a. Zastępowana wcześniejsza decyzja T021 (R2, audyt R1)

`arch/T021_spec.md:401` i `tasks/ROTA-T021/brief.md:167,177` (round-2 audit
A3, „CORRECTED 2026-08-23”) dokumentują jawnie i świadomie: „UI inputs are
exactly three (Nazwa obiektu, Nazwa profilu zmianowego, Próg decyzyjny
7-dniowy)”. T049 jawnie zastępuje tę wcześniejszą, udokumentowaną decyzję —
na podstawie tej późniejszej decyzji OWNERA, nie jako jej przypadkowe
pominięcie. Po T049 UI inputs formularza tworzenia obiektu to dwa, nie trzy
(Nazwa obiektu, Próg decyzyjny 7-dniowy); `SiteProfile.display_name`
przestaje być wejściem koordynatora, staje się wartością pochodną.

## 2. Wybrane brzmienie automatycznej nazwy profilu

`SiteProfile.display_name` nigdzie w programie nie jest czytany poza
jednorazowym zapisem (`rota/persistence/site_profile_repository.py:56`).

**Korekta R2 (audyt R1):** pierwsza wersja tego briefu błędnie twierdziła,
że ta nazwa może się pokazać w widoku „Przed/Po” w Historii
(`History.tsx:64`). To nieprawda — sprawdzone dokładnie:
`rota/application/bootstrap.py::_profile_state` (funkcja serializująca
`SiteProfile` do tego widoku) w ogóle nie zapisuje `display_name` w swoim
słowniku (linia 119-132: tylko `profile_id`, `active`, `standard_shifts`
i pola profilu zmianowego, bez `display_name`). `History.tsx:64` mapuje
klucz `profile_id` → „profil”, nie `display_name`. Usuwana nazwa nie ma
więc dziś ŻADNEGO miejsca odczytu w całym programie, nawet pośredniego.

Brak wymogu unikalności, brak porównań, brak formatu. Najprostsze,
przewidywalne rozwiązanie: skopiować dokładnie to, co koordynator wpisał
jako nazwę obiektu.

### Wymagane zachowanie

`api/routers/bootstrap.py::create_site` (linia 117-145): usunąć pole
`profile_display_name` z `CreateSiteRequest` (linia 40); w konstrukcji
`SiteProfile` (linia 131-142) zamienić `display_name=payload.profile_display_name`
na `display_name=payload.display_name`.

## 3. Formularz i typ żądania (frontend)

`frontend/src/screens/Workspace.tsx` (komponent tworzenia nowego obiektu,
linie ok. 443-510): usunąć `const [profileName, setProfileName] = useState("")`,
cały blok `<label>` z polem „Nazwa profilu zmianowego” (linie 480-487),
`profile_display_name: profileName` z wywołania `api.createSite`, oraz
`!profileName.trim()` z warunku `disabled` przycisku „Utwórz obiekt”.

`frontend/src/api/client.ts` (`CreateSiteRequest`, linia ok. 29-33): usunąć
pole `profile_display_name: string;`.

## 4. Wywołania backendu, które nadal wysyłają usuwane pole

Trzy miejsca w harnessach symulatorów wołają realny endpoint `POST
/workspace/sites` z polem `profile_display_name` w payloadzie — po usunięciu
go z `CreateSiteRequest`, Pydantic odrzuci nieznane pole tylko jeśli model ma
`extra="forbid"`; niezależnie od tego trzeba je usunąć, żeby harnessy nie
udawały nieistniejącego już kontraktu:

- `tests/property/coordinator_simulator.py:339,1186`
- `tests/property/test_coordinator_simulator_variant_b.py:295`

Usunąć klucz `"profile_display_name": ...` z każdego z tych trzech
słowników payloadu, nic więcej w tych plikach się nie zmienia.

## 5. Testy e2e (Playwright) — realny, żywy zasięg tego pola

`frontend/e2e/helpers.ts::createSite(page, displayName, profileName)`
(linia 17-23) wypełnia to pole i jest wołana **26 razy w 6 plikach spec**.
Dwa pliki mają DODATKOWO co najmniej jedno miejsce, gdzie formularz jest
budowany ręcznie, bez tego helpera, wypełniając to pole bezpośrednio po
selektorze placeholdera — jeden z nich w całości (`diagnostics.audit-r1.spec.ts`),
drugi częściowo, obok swoich 8 wywołań helpera
(`diagnostics.spec.ts` — **poprawione R2, patrz niżej**, pierwsza wersja
briefu to przeoczyła). To jest mechaniczna, jednorodna zmiana (usunięcie
jednego argumentu/jednej linii w każdym miejscu), ale dotyczy realnie
ośmiu plików e2e:

- `frontend/e2e/helpers.ts` — usunąć parametr `profileName` z sygnatury
  `createSite` i linię `.fill(profileName)` dla selektora
  `input[placeholder="np. PROF-NORDPLAST-02"]`.
- `frontend/e2e/diagnostics.spec.ts` — 8 wywołań `createSite(page, ..., ...)`
  (linie 38, 62, 101, 117, 130, 147, 155, 202): usunąć trzeci argument z
  każdego. **Korekta R2 (audyt R1):** ten sam plik ma DODATKOWO dwa
  bezpośrednie, ręczne wypełnienia pola poza helperem (linie 57, 96,
  scenariusze błędu/timeoutu backendu) — pierwsza wersja briefu je
  pominęła. Usunąć linię `.locator('input[placeholder="np. PROF-NORDPLAST-02"]').fill(...)`
  w obu miejscach, tak samo jak w `diagnostics.audit-r1.spec.ts` niżej.
- `frontend/e2e/monthly-planning.spec.ts` — 5 wywołań (linie 37, 61, 92,
  114, 143): usunąć trzeci argument.
- `frontend/e2e/shift-catalog.spec.ts` — 5 wywołań (linie 20, 39, 59, 75,
  106): usunąć trzeci argument.
- `frontend/e2e/t041-daily-workflow.spec.ts` — 5 wywołań (linie 107, 121,
  152, 226, 293): usunąć trzeci argument.
- `frontend/e2e/t042-local-date.spec.ts` — 2 wywołania (linie 42, 101):
  usunąć trzeci argument.
- `frontend/e2e/t043-coordinator-confidence.spec.ts` — 1 wywołanie
  (linia 50): usunąć trzeci argument.
- `frontend/e2e/diagnostics.audit-r1.spec.ts` — NIE woła helpera, buduje
  formularz ręcznie: usunąć linię
  `.locator('input[placeholder="np. PROF-NORDPLAST-02"]').fill(...)` w
  dwóch miejscach (linie 27, 76). Reszta obu testów bez zmian.

Żadna asercja w żadnym z tych plików nie sprawdza treści usuwanej nazwy
profilu (sprawdzone: `profile_display_name`/`PROF-` używane tam tylko jako
wartość wejściowa do wypełnienia pola, nigdy jako oczekiwany wynik) —
usunięcie argumentu/linii nie zmienia sensu żadnego z tych testów.

## 6. Co świadomie zostaje bez zmian

- `profile_id` (zawsze losowy `PROF-<uuid>`) — bez zmian, to nie jest to
  samo pole co usuwane `profile_display_name`.
- Żaden inny ekran/formularz nie odwołuje się do profilu zmianowego w
  kontekście tworzenia obiektu — sprawdzone całe repo.
- `tasks/ROTA-T021/round_01/tests/test_t021_r4_audit.py` i
  `test_t021_r5_audit.py` też konstruują `CreateSiteRequest(profile_display_name=...)`,
  ale to zamrożone archiwum audytu zakończonego Tasku (`testpaths = ["tests"]`
  w `pyproject.toml` — katalog `tasks/` nie jest zbierany przez pytest,
  nic tam nie uruchamia się w CI) — nie dotykać, nie są to żywe testy.
- Nazwa obiektu (`displayName`/`Nazwa obiektu`) — bez zmian, to pole
  zostaje dokładnie takie jak jest.

## 7. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Minimalna konieczna zmiana |
|---|---|---|
| backend: pole żądania + auto-nazwa | żywy przykład OWNERA | usunięcie 1 pola z Pydantic modelu, zmiana 1 argumentu w konstruktorze |
| frontend: formularz | żywy przykład OWNERA | usunięcie 1 stanu, 1 bloku pola, 1 klucza payloadu, 1 warunku disabled |
| frontend: typ żądania | konsekwencja usunięcia pola z backendu | usunięcie 1 pola z interfejsu TS |
| harnessy symulatorów (3 miejsca) | konsekwencja zmiany kontraktu | usunięcie 1 klucza ze słownika payloadu w każdym |
| e2e (8 plików, 26+2 miejsc) | konsekwencja usunięcia pola z UI | usunięcie 1 argumentu/1 linii w każdym miejscu, wzorzec identyczny wszędzie |

Usunięte z propozycji jako zbędne: zmiana `profile_id`, dodanie ekranu
edycji profilu, jakakolwiek zmiana logiki solvera/PLAN/katalogu zmian,
ogólny refaktor formularza tworzenia obiektu poza usuwanym polem.

## 8. TASK_SCOPE

Dozwolony kod produktu:

- `api/routers/bootstrap.py`
- `frontend/src/screens/Workspace.tsx`
- `frontend/src/api/client.ts`

Dozwolone testy i dokumenty:

- `tasks/ROTA-T049/brief.md`
- `tests/property/coordinator_simulator.py`
- `tests/property/test_coordinator_simulator_variant_b.py`
- `frontend/e2e/helpers.ts`
- `frontend/e2e/diagnostics.spec.ts`
- `frontend/e2e/diagnostics.audit-r1.spec.ts`
- `frontend/e2e/monthly-planning.spec.ts`
- `frontend/e2e/shift-catalog.spec.ts`
- `frontend/e2e/t041-daily-workflow.spec.ts`
- `frontend/e2e/t042-local-date.spec.ts`
- `frontend/e2e/t043-coordinator-confidence.spec.ts`

Poza zakresem, wymaga zatrzymania i wskazania konkretnej konieczności:

- `rota/planning/**`, solver, walidator
- `rota/persistence/site_profile_repository.py` (tylko odczyt/zapis
  istniejącego pola, bez zmian struktury)
- jakikolwiek inny ekran niż formularz tworzenia obiektu
- `tasks/ROTA-T021/round_01/tests/*` (zamrożone archiwum, sekcja 6)

## 9. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `api/routers/bootstrap.py --symbol CreateSiteRequest`
  - `api/routers/bootstrap.py --symbol create_site`
- REASON: Task usuwa pole z publicznego kontraktu żądania API; trzeba
  potwierdzić wszystkich rzeczywistych nadawców tego pola przed usunięciem,
  żeby żaden nie został z odwołaniem do nieistniejącego już pola.

Wykonane na `BASE_MAIN_SHA` (`where.py`): `CreateSiteRequest` — jedna
definicja produkcyjna, jeden produkcyjny użytkownik w tym samym pliku
(`create_site`), jeden odpowiednik frontendowy (`client.ts`'s
`CreateSiteRequest` interface + `createSite` wywołanie), oraz dwa
odwołania w zamrożonym archiwum `tasks/ROTA-T021/...` (sekcja 6, nie
dotykane). `create_site` — jedna definicja, wołana przez FastAPI router
(brak innego callera produkcyjnego). Frontendowe/e2e wystąpienia sprawdzone
ręcznie `git grep`'em na exact SHA — pełna lista w sekcjach 3-5, żadne inne
miejsce w repo nie odwołuje się do `profile_display_name`/„Nazwa profilu
zmianowego”/placeholdera `PROF-NORDPLAST-02`.

## 10. Macierz odbioru

- **T49-01 — pole zniknęło:** formularz „Nowy obiekt” (oba warianty,
  Ochrona i Standardowy) nie zawiera pola „Nazwa profilu zmianowego”;
  przycisk „Utwórz obiekt” jest aktywny po samym wypełnieniu nazwy obiektu
  (bez drugiego pola).
- **T49-02 — profil dostaje nazwę obiektu:** po utworzeniu obiektu o nazwie
  X, zapisany `SiteProfile.display_name` dla tego obiektu to dokładnie X.
- **T49-03 — `profile_id` bez zmian:** `profile_id` nadal jest świeżym
  losowym `PROF-<uuid>`, niezależnym od nazwy obiektu i od usuniętego pola.
- **T49-04 — harnessy symulatorów działają:** `tests/property/coordinator_simulator.py`
  i `test_coordinator_simulator_variant_b.py` tworzą obiekty przez
  `POST /workspace/sites` bez wysyłania `profile_display_name` i bez błędu.
- **T49-05 — e2e nienaruszone:** wszystkie specy wymienione w sekcji 5
  nadal przechodzą `createSite`/ręczne tworzenie obiektu bez odwołania do
  usuniętego pola.
- **T49-06 — brak regresji poza zakresem:** nazwa obiektu, próg decyzyjny
  7-dniowy i wybór reżimu (Ochrona/Standardowy) działają dokładnie tak jak
  przed Taskiem.

## 11. Weryfikacja proporcjonalna do zmiany

Implementator uruchamia:

- celowane T49-01…T49-06 (T49-02/T49-03 łatwo testowalne jednostkowo na
  `api/routers/bootstrap.py::create_site`; T49-01/T49-05 wymagają realnego
  przebiegu e2e albo ręcznej weryfikacji w przeglądarce z opisem w DELIVERY,
  jeśli pełny e2e runner nie jest dostępny w środowisku implementatora —
  jawnie zaznaczyć które);
- `tests/property/coordinator_simulator.py`/`test_coordinator_simulator_variant_b.py`
  — co najmniej jeden szybki przebieg (kilka seedów), nie pełny batch;
- `ruff check` dla zmienionych plików `.py`;
- lintowanie/typecheck frontendu, jeśli repo ma taki krok skonfigurowany;
- `git diff --check`.

Pełna suita repozytorium (w tym pełny przebieg e2e) jest opcjonalna i
wymaga osobnej zgody OWNERA.

## 12. Proces i oczekiwany werdykt CC

Jedna mechaniczna zmiana (usunięcie jednego pola) o dużym, ale w pełni
jednorodnym zasięgu — ten sam wzorzec powtórzony w wielu plikach testowych,
zero nowej logiki produktu. Architekt nie jest potrzebny, chyba że CC
wykaże konkretną sprzeczność ownership (np. jeśli `profile_display_name`
okaże się jednak gdzieś czytane, czego nie znaleziono na `BASE_MAIN_SHA`).

Oczekiwany werdykt preimplementation:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` tylko z konkretnym `TRACE`, `OWNERSHIP` i reproduktorem sprzeczności.

Do PASS: CC READ-ONLY.

## 13. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T049/brief.md
- api/routers/bootstrap.py
- frontend/src/screens/Workspace.tsx
- frontend/src/api/client.ts
- tests/property/coordinator_simulator.py
- tests/property/test_coordinator_simulator_variant_b.py
- frontend/e2e/helpers.ts
- frontend/e2e/diagnostics.spec.ts
- frontend/e2e/diagnostics.audit-r1.spec.ts
- frontend/e2e/monthly-planning.spec.ts
- frontend/e2e/shift-catalog.spec.ts
- frontend/e2e/t041-daily-workflow.spec.ts
- frontend/e2e/t042-local-date.spec.ts
- frontend/e2e/t043-coordinator-confidence.spec.ts
