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
| `rota/planning/solver.py` | prawdopodobnie bez zmian — potwierdzę dopiero przy implementacji, jeśli brief to obejmie |
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

**Interakcja z EXTERNAL_SUPPORT/can_work_24h/SiteRule.** Sprawdzone wprost w
`eligibility.py::check_eligibility`: `_common_hard_gate` (gdzie żyłaby nowa
bramka kategorii) wykonuje się PRZED rozgałęzieniem na
`membership_kind == LOCAL` vs `EXTERNAL_SUPPORT`. Oznacza to konkretne
pytanie do briefu: czy kategoria ma w ogóle dotyczyć `EXTERNAL_SUPPORT`
(wsparcie zewnętrzne to koncepcja z Ochrony, obcy sklepowi), czy nowa
bramka powinna być pomijana dla `EXTERNAL_SUPPORT` tak jak dziś część
innych reguł jest pomijana dla tego membership_kind. `can_work_24h`
współistnieje bez konfliktu (inna bramka, inny warunek). SiteRule: bez
zmian, `_blocked_by_site_rules` działa niezależnie od kategorii.

**Układ wydruku.** Nierozstrzygnięte — to decyzja UX (nagłówki sekcji per
kategoria? kolejność kategorii? osobna tabela per kategoria?), nie techniczna.
Do briefu/architekta.

**Jeden Task czy dwa.** Rekomendacja CC: **dwa Taski.** Backend (domain +
shift_catalog + eligibility) jest wąski, addytywny, testowalny w izolacji
(dokładnie jak T012) i nie wymaga UX. Wydruk z grupowaniem dotyka innego
pliku (`schedule_export.py`), innej warstwy (prezentacja, nie eligibility) i
wymaga osobnej decyzji UX — łączenie ich w jeden Task tylko powiększa diff
bez żadnego technicznego sprzężenia między nimi. Druga zmiana (wydruk) może
zacząć się dopiero gdy backend ma już wartość kategorii do wyświetlenia, ale
to kolejność, nie powód łączenia w jeden brief/audit.

## 4. Poza zakresem tej oceny

CC nie proponuje: nazwy pola, dokładnego zestawu wartości enuma kategorii,
kształtu wydruku, ani czy "ekipa sprzątająca" wchodzi teraz. To wszystko
należy do briefu architekta po decyzjach Pawła.
