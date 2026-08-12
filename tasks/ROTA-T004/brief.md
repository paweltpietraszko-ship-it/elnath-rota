# TASK_CONTRACT

TASK_ID: ROTA-T004
TITLE: SiteProfile persistence
STATUS: ARCHITECTURE_APPROVED_FOR_IMPLEMENTATION
DATE: 2026-08-12
BASE_MAIN_SHA: 2da73294712f8c77d089d659883ea44513668416
ARCHITECT_ROLE: ChatGPT architect
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: ChatGPT architect
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes

## PURPOSE / WORKFLOW TRACE

Ten plik jest artefaktem architektonicznym pozostawionym celowo w repo, aby można było później odtworzyć workflow i provenance decyzji.

Podział ról:
- architekt projektuje Task Contract i rozstrzyga kwestie techniczne w granicach kanonu;
- CC implementuje wyłącznie zaakceptowany zakres;
- Codex audytuje implementację względem kontraktu i frozen spec;
- po audycie rezultat wraca do architekta do finalnego architectural PASS/FAIL;
- materialne decyzje produktowe pozostają po stronie właściciela.

## SOURCE FACTS

Frozen `arch/spec.md` definiuje `SiteProfile` i mówi, że jego pola są konfigurowalne przez koordynatora, a reguły są danymi, nie logiką w kodzie.

`PlanningState.profile` przyjmuje gotowy `SiteProfile`.

`PlanningEngine` nie może posiadać persistent business state ani wykonywać I/O.

W bazowym SHA repo nie istnieje warstwa trwałości domeny Rota.

## OBJECTIVE

Dodać minimalną lokalną persystencję `SiteProfile` potrzebną Rota.

Po restarcie programu profil musi dać się odtworzyć dokładnie z trwałej pamięci.

Nie zmieniać semantyki `SiteProfile`, PlanningEngine ani zasad grafiku.

## ARCHITECTURE DECISION

Rota używa własnej lokalnej bazy SQLite.

T004 tworzy wspólną podstawę persistence, z której może skorzystać późniejszy T005.

Persistence znajduje się poza `rota/planning/`.

PlanningEngine:
- nie otwiera bazy;
- nie zna ścieżki bazy;
- nie zapisuje danych;
- nie odczytuje danych.

`PlanningState.profile` nadal otrzymuje gotowy obiekt `SiteProfile`.

## DOMAIN BOUNDARY

Persistowane są dokładnie istniejące pola `SiteProfile`:
- `profile_id`
- `display_name`
- `active`
- `standard_shifts`
- `day_only_blocks_n`
- `external_support_enabled`
- `training_s_enabled`
- `training_s_weekdays_only`
- `training_s_default_readiness_threshold`
- `rolling_7d_decision_threshold_hours`

Każdy `StandardShift` zachowuje:
- `kind`
- `start_time`
- `end_time`
- `end_next_day`
- `required_primary_count`

Nie dodawać nowych pól produktu.

## STORAGE MODEL

Jedna tabela przechowuje bieżący `SiteProfile`.

Osobna tabela przechowuje uporządkowaną listę `StandardShift` należących do profilu.

Kolejność `standard_shifts` musi być zachowana przy round-trip.

Zmiana profilu jest atomowym zapisem bieżącego stanu razem z jego `standard_shifts`.

## NO SITEPROFILE VERSIONING

T004 nie tworzy:
- `SiteProfileVersion`;
- historii zmian profilu;
- `profile_version_id`;
- relacji `ScheduleVersion` do wersji profilu.

Aktualny kontrakt jawnie wersjonuje `SiteRuleVersion` i `ScheduleVersion`, ale nie definiuje wersjonowania `SiteProfile`.

Decyzja architektoniczna dla pilota: nie dokładamy mechanizmu, którego produkt obecnie nie wymaga.

## PERSISTENCE RESPONSIBILITY

Warstwa persistence ma zapewnić wyłącznie operacje potrzebne do bieżącego stanu:
- zapis profilu;
- odczyt profilu po `profile_id`;
- odczyt listy istniejących profili.

Nie dodawać repository framework, Unit of Work, event sourcing, cache layer ani abstrakcji przygotowanych wyłącznie „na przyszłość”.

## DATABASE FOUNDATION

T004 tworzy prostą wspólną warstwę połączenia i inicjalizacji schema dla lokalnej bazy Rota.

Ścieżka pliku bazy jest przekazywana przez caller.

Nie hardkodować finalnej lokalizacji desktopowego pliku danych.

Nie budować rozbudowanego frameworka migracyjnego. Dla pilota wystarczy idempotentna inicjalizacja aktualnego schema.

## TRANSACTION RULE

Zapis profilu i jego `standard_shifts` jest jedną transakcją.

Nie może istnieć widoczny stan pośredni, w którym profil został zapisany, a lista zmian jest częściowo stara albo częściowo nowa.

## DELETE

Nie jest potrzebne fizyczne kasowanie profilu.

Istniejące pole `active` służy do wyłączenia profilu.

Nie projektować dodatkowego lifecycle.

## TASK_SCOPE

Dozwolone nowe/zmieniane obszary:
- nowy pakiet persistence Rota;
- schema lokalnej bazy;
- persistence/repository dla `SiteProfile`;
- testy persistence T004;
- minimalna konfiguracja projektu konieczna wyłącznie do wykonania zadania.

## OUT_OF_SCOPE

Nie implementować:
- UI;
- desktop bridge;
- SiteRule/SiteMemory;
- Elnath Memory Engine;
- ScheduleVersion persistence;
- Assignment persistence;
- WorkBalance persistence;
- Calendar persistence;
- natural-language rules;
- nowych zasad grafiku;
- zmian PlanningEngine;
- zmian `arch/spec.md`.

## ACCEPTANCE CONTRACT

PASS wymaga łącznie:
1. `SiteProfile` zapisany do trwałej pamięci daje się odczytać po ponownym otwarciu bazy.
2. Wszystkie istniejące pola zachowują wartości.
3. `standard_shifts` zachowują komplet danych i kolejność.
4. Ponowny zapis istniejącego `profile_id` zmienia bieżący stan profilu bez tworzenia ukrytej historii wersji.
5. Zapis profilu i shifts jest atomowy.
6. `active=false` pozostaje normalnie odczytywalnym stanem.
7. PlanningEngine nie wykonuje żadnego I/O i nie importuje persistence.
8. T004 nie wprowadza nowych reguł produktu.
9. T004 nie zmienia `arch/spec.md`.
10. Brak dodatkowych frameworków i warstw niepotrzebnych do powyższej funkcji.

## PROCESS

Po przyjęciu tego Task Contract implementer uruchamia repozytoryjny workflow task init dla `ROTA-T004`, o ile struktura zadania nie istnieje już z tego artefaktu architektonicznego; w takim przypadku nie wolno nadpisać niniejszego pliku i należy zachować provenance/base SHA ręcznie w artefaktach rundy.

CC implementuje wyłącznie Task Scope.

Codex audytuje względem tego Task Contract + frozen `arch/spec.md`.

Po audycie DELIVERY wraca do architekta do finalnego PASS/FAIL.
