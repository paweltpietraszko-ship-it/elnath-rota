# T065 — wstępna ocena zakresu (CC, przed briefem architekta)

Uzupełnienie do `arch/FINDING_2026-09-03_STANDARDOWY_EMPLOYEE_CATEGORIES.md`
(OWNER_CONFIRMED 2026-09-10, BOARD.md). Nie jest to projekt rozwiązania ani
brief — to doprecyzowanie mapy dotknięcia i otwartych pytań z findingu na
podstawie bezpośredniego odczytu kodu, żeby architekt miał mniej do
odkrywania przy pisaniu briefu. Decyzje produktowe poniżej są rekomendacjami
do potwierdzenia przez Pawła/architekta, nie ustaleniami.

## 1. Potwierdzony wzorzec addytywny (nie nowy)

Dokładnie ten kształt zmiany już trzykrotnie przeszedł przez ten kod:

- `SiteMembership.can_work_24h` (ROTA-T012) — pole per (employee, site),
  domyślne `True`, konsumowane przez jedną twardą bramkę w
  `eligibility.py::_common_hard_gate` (`SHIFT-24-01`), zero zmian w
  `solver.py`.
- `StandardShift.catalog_kind` / `active_weekdays` (ROTA-T012) — pola na
  definicji zmiany w `SiteProfile`, płynące przez
  `shift_catalog.py::_components_to_demands` do `ShiftDemand.catalog_kind`,
  konsumowane w eligibility jako dodatkowy warunek bramki.

Kategoria pracownika pasuje do dokładnie tego samego kształtu: nowe pole na
`StandardShift` (który pracownik może obsłużyć tę zmianę), płynące przez
`_components_to_demands` do `ShiftDemand`, i nowa twarda bramka w
`_common_hard_gate` porównująca kategorię z `SiteMembership` do kategorii
wymaganej przez `ShiftDemand` — analogicznie do `SHIFT-24-01`. Solver.py
najprawdopodobniej bez zmian strukturalnych (jedna dodatkowa twarda bramka
przed CP-SAT, nie nowa zmienna decyzyjna).

## 2. Doprecyzowanie mapy dotknięcia z findingu

| Plik | Rola w tej zmianie |
|---|---|
| `rota/domain.py` | nowe pole kategorii na `SiteMembership` (rekomendacja, patrz §3) i na `StandardShift`/`ShiftDemand` (wymagana kategoria zmiany) |
| `rota/planning/shift_catalog.py` | `_components_to_demands` przenosi kategorię z `StandardShift`/`_Component` do `ShiftDemand`, dokładnie jak dziś robi to z `catalog_kind` |
| `rota/planning/eligibility.py` | nowa twarda bramka w `_common_hard_gate`, obok istniejącej `SHIFT-24-01`; pytanie o interakcję z `EXTERNAL_SUPPORT` w §4 |
| `rota/planning/validator.py` | **DODANE po korekcie Codexa (precheck `bf359d1`).** Niezależny HARD validator (osobny od solvera i od `eligibility.py`), sprawdza istniejące/ręczne `Assignment` po fakcie — np. `_check_membership_enabled`, `_check_day_only`, `_check_external`. Nowa bramka kategorii w `eligibility.py` zabezpiecza tylko GENEROWANIE nowych slotów; bez odpowiednika tutaj ręczna edycja lub REPLAN mogłyby po cichu naruszyć regułę kategorii bez wykrycia. |
| `rota/planning/solver.py` | prawdopodobnie bez zmian — potwierdzę dopiero przy implementacji, jeśli brief to obejmie |
| `rota/persistence/db.py` + repozytoria (`employee_repository.py::save_site_membership`, katalog zmian) | **DODANE po korekcie Codexa.** Migracja schematu i ścieżka trwałego zapisu nowego pola — bez tego kategoria nie ma jak przetrwać poza pojedynczym requestem. |
| `api/routers/roster.py`, `api/routers/durable_inputs.py`, `api/routers/site_profile.py` | **DODANE po korekcie Codexa.** Wejścia, którymi koordynator faktycznie ustawia kategorię na membership/katalogu zmian — bez tego backend ma pole, ale nikt nie może go wypełnić. |
| `frontend/src/screens/ControlPanel.tsx`, `EmployeeDetail.tsx`, `SiteShiftCatalog.tsx` | **DODANE po korekcie Codexa.** Ekrany, na których koordynator dziś zarządza membership/katalogiem — realistycznie potrzebują UI do kategorii, żeby funkcja była w ogóle używalna, nie tylko API. |
| `rota/application/schedule_export.py` | `_build_rows` (linia ~601) dziś iteruje `roster_ids` czysto alfabetycznie, zero pojęcia grupowania — wydruk z kategoriami to osobna, nietrywialna zmiana UI/eksportu, nie samo dodanie pola |

## 3. Otwarte pytania z findingu — stan po sprawdzeniu kodu

**Employee vs SiteMembership.** Istniejący precedens (`can_work_24h`) leży na
`SiteMembership`, nie na `Employee` — czyli per (pracownik, obiekt), nie
globalnie per pracownik. Dla spójności z istniejącym wzorcem i dlatego że
kategoria w realnym scenariuszu (sklep) jest właściwością roli NA TYM
obiekcie, rekomendacja: `SiteMembership`. Zastrzeżenie: to nadal decyzja
produktowa (czy ten sam pracownik mógłby być "kierownikiem" na jednym
obiekcie i "załogą" na innym) — potwierdzenie należy do Pawła/architekta,
nie do CC.

**"Ekipa sprzątająca".** Finding już to nazwał "jawnie niepewne" — nie
znalazłem żadnego dodatkowego faktu w kodzie, który by to rozstrzygał. Nadal
otwarte, do decyzji Pawła.

**Interakcja z EXTERNAL_SUPPORT/can_work_24h/SiteRule — SKORYGOWANE po
uwadze Pawła (2026-09-13).** Pierwotne założenie w tej sekcji było błędne:
"wsparcie zewnętrzne to koncepcja z Ochrony, obca sklepowi". Paweł
sprostował wprost: "W sklepach jak mojej żony gdzie jest 10 punktów,
wsparcie zewnętrzne jako przejście jednego pracownika na inny punkt jest
częste." Czyli w realnym docelowym scenariuszu (sieć kilku/kilkunastu
sklepów) `EXTERNAL_SUPPORT` NIE jest brzegowym przypadkiem do pominięcia —
jest zwyczajnym, częstym mechanizmem. To podnosi konkretne pytanie do
briefu, ostrzejsze niż wcześniej sformułowane: gdy pracownik z obiektu A
(np. "kierownik") pokrywa zmianę na obiekcie B jako `EXTERNAL_SUPPORT`, czy
musi to być zmiana wymagająca tej samej kategorii ("kierownik" pokrywa
tylko zmiany kierownicze), czy `EXTERNAL_SUPPORT` z definicji pomija bramkę
kategorii (dowolna kategoria pokrywa dowolną zmianę jako wsparcie)? Sam kod
nie rozstrzyga tego — `_common_hard_gate` wykonuje się PRZED rozgałęzieniem
na `membership_kind == LOCAL` vs `EXTERNAL_SUPPORT`, więc technicznie da
się zaimplementować którąkolwiek odpowiedź; to czysto produktowa decyzja
do briefu/Pawła, nie coś do rozstrzygnięcia przez CC. `can_work_24h`
współistnieje bez konfliktu (inna bramka, inny warunek). SiteRule: bez
zmian, `_blocked_by_site_rules` działa niezależnie od kategorii.

**Układ wydruku.** Nierozstrzygnięte — to decyzja UX (nagłówki sekcji per
kategoria? kolejność kategorii? osobna tabela per kategoria?), nie techniczna.
Do briefu/architekta.

**Jeden Task czy dwa.** Rekomendacja CC: **dwa Taski** — podtrzymana, ale ze
skorygowanym uzasadnieniem po uwadze Codexa. Backend (domain + persistence +
shift_catalog + eligibility + validator + API + ekrany zarządzania) jest
większy niż pierwotnie napisałem, ale nadal jedna spójna, testowalna w
izolacji całość (analogicznie do tego, jak T012 objął domain+eligibility+UI
razem). Wydruk z grupowaniem to osobna warstwa (prezentacja), ale **zdanie
"bez żadnego technicznego sprzężenia" było za mocne — Codex słusznie to
złapał**: wydruk zależy od trwale zapisanej kategorii, więc backend Task
musi się skończyć pierwszy, a brief musi rozstrzygnąć, z jakiego źródła
wydruk grupuje wiersz — z BIEŻĄCEGO membership w momencie druku, czy z
migawki (snapshot) kategorii zapisanej przy generowaniu grafiku/demandu —
bo to wpływa na to, czy wydruk historycznego miesiąca zmienia się, gdy
kategoria pracownika zmieni się później. To pytanie do briefu, nie
rozstrzygnięcie CC.

## 4. Poza zakresem tej oceny

CC nie proponuje: nazwy pola, dokładnego zestawu wartości enuma kategorii,
kształtu wydruku, ani czy "ekipa sprzątająca" wchodzi teraz. To wszystko
należy do briefu architekta po decyzjach Pawła.
