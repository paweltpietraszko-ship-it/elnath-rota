# ROTA-T010-B — jedna matryca dostępności pracownika

STATUS: DRAFT FOR CODEX AUDIT

Dla nowego zwykłego pracownika bazowo: Ogólna dostępność ✓, Dniówka ✓, Nocka ✓, Pon–Nd ✓. Każdy ptaszek ma jedno znaczenie: `✓` = solver może korzystać, `☐` = solver nie może korzystać w obowiązującym okresie. `od–do` jest włączne; po `do` wraca stan bazowy bez operacji przywracającej. Jedno właściwe `☐` wystarcza do blokady.

Dla czasowych ograniczeń dotyczących Site użyć istniejącego `SiteRuleVersion` i `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`:

- Ogólna dostępność ☐ bez powodu nieobecności: weekdays 1..7, forbidden D,N;
- Dniówka ☐: weekdays 1..7, forbidden D;
- Nocka ☐: weekdays 1..7, forbidden N;
- dni tygodnia ☐: wybrane weekdays, forbidden D,N.

Dniem jest data rozpoczęcia ShiftDemand, także dla N. Niezależne decyzje/zakresy używają oddzielnych istniejących rodzin SiteRule, aby nie nadpisywały się wzajemnie. Nie tworzyć panelowych tabel ani booleanów.

Jeżeli Ogólna dostępność ☐ oznacza chorobę lub udzielony urlop, użyć istniejącego `AvailabilityRecord`: odpowiednio `SICK_LEAVE` albo `LEAVE_GRANTED`. Nie tworzyć dla tego samego faktu dodatkowego SiteRule. `NN` nie jest dostępnością przed planowaniem i należy do T010-D.

`Employee.day_only` pozostaje jedynym bazowym źródłem stałego zakazu N. Dla `day_only=true` bazowy stan Nocki jest ☐. Czasowe Nocka ✓ od–do ma być datowanym `SiteRuleVersion` kategorii `CONFIRMED_EXCEPTION` z istniejącym `EMPLOYEE_ALLOWED_SHIFT_KINDS` obejmującym N. To wąski wyjątek tylko od DAY_ONLY-01 dla danego employee/Site/daty, nie ogólny mechanizm łamania HARD. Wszystkie pozostałe HARD nadal składają się przez AND. Eligibility i validator muszą działać identycznie. Po `effective_to` znów działa `day_only`.

Dodać małą projekcję application layer dla T012, która składa Employee/AvailabilityRecord/SiteRuleVersion do bazowego stanu i datowanych ograniczeń/wyjątków. Projekcja niczego nie zapisuje i nie wymusza na UI znajomości `rule_kind`.

Testy: wszystkie bazowo ✓; Ogólna ☐; D ☐; N ☐; Piątek ☐; nakładanie ograniczeń; SICK/LEAVE bez duplikatu SiteRule; `day_only` + czasowe N ✓; zgodność solvera i validatora.

FAIL za odwrócone znaczenie ptaszka, drugi `day_only`, równoległy stan dostępności, automatyczne łamanie HARD albo ogólny mechanizm „exception overrides everything”.