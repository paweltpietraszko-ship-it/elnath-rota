# Handoff brief for architect: solver communicates real options to the coordinator (proponowane T013)

## Status

**GOTOWE DO PRZEKAZANIA ARCHITEKTOWI — decyzje produktowe właściciela zamknięte 2026-08-15/16.**

Warunki wejściowe T012 + T016 są spełnione.

Aktualizacja wejściowa 2026-08-19: architekt projektuje T013 na aktualnym `main` również po zmergowaniu T018. T013 nie może cofnąć nowej kolejności fallbacków ani proponować zmiany DAY_ONLY zanim istniejące automatyczne próby T018 zostaną wyczerpane.

Ten dokument jest faktograficznym owner handoff. Nie proponuje architektury tłumaczenia ani techniki dynamicznego sprawdzania opcji.

## Skąd to zadanie

Po analizie realnego audytu T011-INTEGRATION właściciel wskazał problem: przy `DECISION_REQUIRED` program ma realne możliwości, ale komunikat wymaga od koordynatora znajomości wewnętrznej architektury i kodów.

Program ma komunikować koordynatorowi, co może zrobić, gdy solver utknie. Komunikat ma być zrozumiały dla zwykłego użytkownika, bez technicznego żargonu.

T013 jest świadomie oddzielone od T012 24h. To zmiana sposobu raportowania istniejących opcji, nie nowa reguła planowania.

## Aktualny stan — cztery końcowe ścieżki DECISION_REQUIRED

Wszystkie są w `rota/planning/engine.py` i budują istniejący `DecisionRequiredPayload` (`blocking_shift_demands`, `blockers`, `load_blocker`, `unblocking_options`).

1. `_decision_for_unassignable` — brak wystarczającej liczby uprawnionych pracowników dla demandu; historycznie statyczne opcje zawierają m.in. `potwierdzenie X/Y`, ściągnięcie pracownika z wolnego, override urlopu i wyłączenie DAY_ONLY.
2. `_decision_for_conflict` — konflikt REST-01 pomiędzy demandami; historycznie jedna ogólna ręczna korekta.
3. `_decision_for_conflicts` — konflikt na zachowanym/frozen Assignment; historycznie odmrożenie, ręczna korekta i opcjonalnie akceptacja LOAD.
4. `_load_decision` — przekroczenie tygodniowego progu godzin; historycznie statyczna akceptacja przekroczenia.

Po T018 te ścieżki są końcowe dopiero po aktualnych automatycznych próbach engine. T013 nie pokazuje wcześniejszych prób jako rozwiązań.

## Wsparcie zewnętrzne — stan faktyczny

Mechanizm wsparcia zewnętrznego istnieje (`SiteProfile.external_support_enabled`, `SiteMembership(kind=EXTERNAL_SUPPORT)`, `ExternalSupportWindow`) i solver go używa, jeżeli dane wejściowe go dopuszczają.

Historyczne `potwierdzenie X/Y` jest technicznym żargonem odnoszącym się do wsparcia zewnętrznego. Koordynator nie powinien widzieć nazwy `X/Y`.

Pozostałe historyczne listy nie wspominają wsparcia zewnętrznego. Wszystkie listy są statyczne, a właściciel chce opcji zależnych od konkretnej sytuacji.

## Blocker.condition — stan faktyczny

`Blocker.condition` jest dziś `str` i może zawierać raw code, np. `REST-01`, `DAY_ONLY-01`, `SICK_LEAVE-01`, `LEAVE_GRANTED-01`, albo dokładny `rule_version_id` SiteRule.

Koordynator nie powinien musieć znać tych technicznych identyfikatorów.

## Decyzje właściciela — zamknięte

### 1. Dynamiczność

`unblocking_options` mają przestać być statyczną listą per typ ścieżki/reguły.

Program ma proponować tylko to, co jest realnie związane z daną konkretną sytuacją, albo wprost poinformować koordynatora, że przy dostępnej obsadzie/układzie nie da się automatycznie przygotować grafiku.

Właściciel pozostawił architektowi wybór techniki: dodatkowa symulacja lub prostsza heurystyka per blocker.

### 2. Koordynator widzi wynik, nie drogę solvera

Koordynatora interesuje kompletny, poprawny grafik, nie przebieg prób solvera.

Solver może wykonywać wewnętrznie kolejne próby/fallbacki, ale na zewnątrz zwraca:
- kompletny poprawny grafik, albo
- końcowe `DECISION_REQUIRED` z konkretną decyzją koordynatora.

Po T018 oznacza to bezwzględnie zachowanie aktualnej kolejności automatycznych fallbacków przed końcowym komunikatem.

### 3. Zakres

T013 obejmuje wszystkie cztery końcowe ścieżki `DECISION_REQUIRED` naraz, nie pilotaż jednej ścieżki.

### 4. Odbiorca / auth

Odbiorcą jest koordynator obiektu lub jego zmiennik.

T013 nie tworzy nowej warstwy technicznej/administracyjnej, logowania ani uprawnień.

### 5. Exact ludzkie zamienniki kodów

| Kod | Tekst dla koordynatora |
|---|---|
| `UNAVAILABLE-01` | `Koliduje z checkbox: Ogólna dostępność` |
| `DAY_ONLY-01` | `Koliduje z checkbox: Nocka` |
| `SICK_LEAVE-01` | `Koliduje z zapisem: Chorobowe` |
| `LEAVE_GRANTED-01` | `Koliduje z zapisem: Urlop` |
| `REST-01` | `Koliduje z odpoczynkiem dobowym` |
| `LOAD-01` | `Koliduje z tygodniowym czasem pracy` |
| `EXTERNAL-01` | `Wsparcie zewnętrzne` |
| `EXTERNAL_SUPPORT_DISABLED` | `Wsparcie zewnętrzne` |
| `MEMBERSHIP_DISABLED` | niewidoczny dla koordynatora |
| `EMP-02` | nie dotyczy po T016 |
| `DAY_SHIFT_OFF-01` | decyzja/nazwa odłożona; T013 zostawia kod bez tłumaczenia |
| dowolny `rule_version_id` SiteRule | koordynator widzi opis zapisanej reguły, nie techniczny id |

`MEMBERSHIP-01` jest traktowany tak samo jak `MEMBERSHIP_DISABLED`: nie pojawia się na liście pokazywanej koordynatorowi.

Tylko koordynator decyduje, kto należy do bieżącej obsady. Program nie proponuje automatycznego dodawania konkretnego kandydata odrzuconego przez membership.

### 6. Wsparcie zewnętrzne po ludzku

Mechanizm `ExternalSupportWindow` pozostaje dostępny, mimo że w praktyce nie jest dziś często konfigurowany z góry.

Komunikat może informować o możliwości wsparcia zewnętrznego, ale nie ma rozbudowywać nowego subsystemu ani używać żargonu `X/Y`.

### 7. SiteRule

Dla blockera wynikającego z SiteRule koordynator ma widzieć opis zapisanej reguły, nie `rule_version_id`.

Sposób pobrania/reprezentacji opisu jest decyzją techniczną architekta.

### 8. Spójność z Panelem Sterowania

Tam, gdzie Panel Sterowania ma już ustaloną nazwę pola/checkboxa, komunikat solvera używa tej samej nazwy.

Znane nazwy:
- `UNAVAILABLE-01` -> `Ogólna dostępność`;
- `DAY_ONLY-01` -> `Nocka`;
- choroba / urlop zgodnie z ustalonymi zapisami;
- nowa kwalifikacja T012 -> dokładnie `24`;
- katalog obiektu T012 -> dokładnie `24h / 12h / INNY`, jeżeli komunikat kiedykolwiek odnosi się do typu zmiany.

REST nie ma checkboxa; używa exact tekstu właściciela z tabeli.

## Otwarte pytania techniczne pozostawione architektowi

1. Gdzie umieścić tłumaczenie raw code -> tekst koordynatora: osobny pure owner czy logika w engine.
2. Jak realizować dynamiczne opcje: symulacja counterfactual czy prostsza heurystyka per realny blocker.

Decyzje produktowe są zamknięte. Te dwa wybory są techniczne i należą do architekta, pod warunkiem zachowania wszystkich powyższych granic.
