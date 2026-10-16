# ROTA-UNMAPPED-DEVIATION-RULES — ręczna korekta bez wymaganej roli

STATUS: READY FOR INDEPENDENT PREIMPLEMENTATION CHECK; IMPLEMENTATION HOLD.
DATA: 2026-10-16.
BASE_SHA: 3b7e60c26124cec7f1b88d359108ba83d4074d17.
BRANCH: codex/rota-unmapped-deviation-rules.

## 1. Cel i źródło

Usunąć brak mapowania ROLE-01, który przerywa zapis świadomej ręcznej korekty
w sklepie: koordynator wskazuje osobę bez wymaganej roli, walidator wykrywa
naruszenie, lecz `materialize_deviations` nie umie nadać mu kategorii.

Źródła PRODUCT_TRUTH:
- `tasks/ROTA-T065/brief.md`, szczególnie właściciel ról w SiteMembership
  i T65-A11: reuse istniejących manual correction/deviation/action trail;
- `tasks/ROTA-T009/brief.md`, istniejący mechanizm świadomej ręcznej korekty;
- OWNER_ACCEPTED 2026-10-16, rozmowa o F1: „Tak, koordynator ma wszelkie prawa
  łamać zasady bo to jego odpowiedzialność, Rota sama zasad nie łamie zasady
  przestrzega a decyzje Koordynatora zapisuje w pamięci.”;
- ta sama decyzja utrwalona w `tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md`, O5;
  O4 wymaga komunikowania wszystkich wykrytych naruszeń;
- OWNER 2026-10-16 wskazał nowy wpis BOARD jako kolejny błąd rodziny F1
  dotyczący wymaganej roli w sklepie.

Dowód wejściowy, nie decyzja produktu: zgłoszenie CC w BOARD,
ROTA-UNMAPPED-DEVIATION-RULES, exact zgłoszenia `8512553`.
CC ustalił problem ze źródła; nie uruchomił reproduktora. Autor briefu
potwierdził na BASE_SHA brak ROLE-01 w mapowaniu, emisję tego kodu przez
`validator_checks_availability._check_role` i istniejącą polską etykietę
w routerze schedule.
Nie jest to niezależny audyt implementacji ani potwierdzenie runtime REPRO.

## 2. Zamrożone zachowanie i minimalna zmiana

Wyzwalacz: koordynator w ORDINARY ręczną korektą przypisuje do zmiany osobę,
której dopuszczone role na tym obiekcie nie pokrywają wymaganej roli demandu.

Efekt: korekta zostaje zapisana istniejącą ścieżką, a ROLE-01 staje się
Deviation w istniejącej kategorii PREFERENCE, jak MEMBERSHIP-01. To użycie
obecnej kategorii dla ograniczenia dopuszczenia na obiekcie, bez nowej reguły
i bez kwalifikowania braku roli jako naruszenia LAW.

Owner produkcyjny: `rota/application/deviation_mapping.py`, wyłącznie
`_BUILTIN_RULE_CATEGORY`: dodać ROLE-01 → DeviationCategory.PREFERENCE.
Nie zmieniać `category_for_rule`, `_affected_target` ani walidatora.
UnknownDeviationSource dla nierozpoznanych źródeł nadal zgłasza błąd;
nie dodawać ogólnego fallbacku, który zamieniałby nieznany problem w preferencję.

Używane dane: obecne SiteMembership, wymaganie roli w ShiftDemand, istniejące
Assignment i wynik walidacji. Zapisywane dane: potomna wersja z poprawką,
Deviation ROLE-01 i dotychczasowy CoordinatorAction z faktami decyzji.
Nie dopisywać osobie dopuszczenia do roli i nie zmieniać katalogu obiektu.
Jednorazowa decyzja w grafiku nie uprawnia automatu do późniejszych
samodzielnych odstępstw i nie tworzy trwałej reguły zastępowania ról.

UI: po zapisie i odświeżeniu istniejąca lista odchyleń pokazuje już obecną
etykietę „brak wymaganej roli”; aktualny banner naruszeń pozostaje zasilany
obecną walidacją. Nie tworzyć nowego panelu, komunikatu zgody ani endpointu.
Istniejąca finalizacja nadal wymaga potwierdzenia aktualnego zestawu odchyleń.
Eksport korzysta z istniejącej polityki kategorii; samo ROLE-01 nie staje się
nowym LAW wymagającym jednorazowego potwierdzenia wydruku.

Błąd zapisu zachowuje obecną atomowość: nie zostawia połowy wersji lub
połowy śladu decyzji. Koordynator może ponowić operację albo wybrać osobę
z właściwą rolą. Nie dodawać logów z danymi osobowymi ani nowej pamięci.

Automat nadal stosuje istniejące `role_covers`: PLAN/REPLAN i akceptacja
automatycznego kandydata nie uzyskują wyjątku przez nowe mapowanie.
Zapis naruszenia jest właściwością świadomej korekty człowieka.

## 3. Redukcja przed implementacją — jedno przejście

SOURCE: decyzja OWNERA o odpowiedzialności człowieka oraz T65-A11.
NECESSITY: brak jednej pozycji w istniejącej tabeli uniemożliwia dojście
do obecnego zapisu odchylenia i decyzji. Wystarcza to mapowanie.

Pozostają dotychczasowi ownerzy ról, walidacji, wersji, pamięci i prezentacji.
Nie są potrzebne zmiany UI/API, nowa walidacja, nowe pola ani refaktor.
Test integracji dowodzi naprawionego szwu; nie odtwarza całego kontraktu ról.
Autor nie wystawia niezależnego PASS własnemu briefowi.

## 4. Minimalny dowód po implementacji

R1. Zachować najmniejszy reproduktor: legalna baza ORDINARY i istniejący
grafik; aktywny lokalny pracownik bez roli wymaganej przez demand;
`apply_manual_correction` przypisuje mu tę zmianę. Na BASE problemem powinno
być UnknownDeviationSource dla ROLE-01, na exact SHA poprawki zapis przechodzi.
Jeżeli rzeczywisty reproduktor nie dochodzi do tego miejsca, zgłosić różnicę
dowodu zamiast zmieniać dane/kontrakt na ślepo.

R2. W tym samym pionie odczytać z bazy dziecko, Deviation ROLE-01/PREFERENCE
i CoordinatorAction wskazujący tę korektę; rodzic i SiteMembership pozostają
bez zmian. Odczyt miesiąca przez rzeczywisty router pokazuje istniejącą polską
etykietę. To dowód zapisu i prezentacji przez obecny szew, nie mock mapowania.

R3. Mała kontrola negatywna: osoba dopuszczona do wymaganej roli nie dostaje
ROLE-01. Dodatkowo użyć istniejącego testu automatycznego planowania ról
z `tests/test_t065_ordinary_roles.py`,
aby potwierdzić, że automat nadal odrzuca niewłaściwą obsadę. Nie kopiować
pełnej macierzy ról, GUI i eksportu; ich kontrakty nie zmieniają się.

R4. Nierozpoznany kod w `category_for_rule` nadal daje UnknownDeviationSource;
niezależny audyt nie może uznać ogólnego catch/fallback za naprawę.

Testy przez `.venv\Scripts\python.exe -m pytest` — w worktree można użyć
pełnej ścieżki interpretera z głównego repo. Uruchomić nowy test i celowane
istniejące testy mapowania/ról. Bez pełnej regresji; wymagałaby osobnej zgody
i uzasadnienia ryzyka zgodnie z AGENTS. Bez testów produktu na etapie briefu.
FAIL tylko przez TRACE + OWNERSHIP + niezależny REPRO na exact SHA.

## 5. Pozostałe kody zgłoszenia i wyłączenia

WORK_PERIOD-01, FULL_HOUR-01, SITE_RULE-01 i ASSIGN pozostają zgłoszone,
lecz poza literalnym zakresem tej korekty. Nie mają w tym briefie nowej
kategorii ani zgody na zapis dowolnego niepoprawnego stanu. Część opisuje
integralność danych, a SITE_RULE-01 może oznaczać brak możliwości sprawdzenia
reguły, nie naruszenie konkretnego wymagania klienta. Sam brak wpisu w tabeli
nie dowodzi, że należy zamienić taki przypadek w zapisywalne odstępstwo.
Nie przenosić na nie kategorii ROLE-01 ani tworzyć dla nich testów nowego
zachowania. Dalszy kontrakt wymaga ustalenia realnej osiągalnej operacji,
właściwego ownera i ewentualnej decyzji OWNERA.

Poza zakresem także: zmiana solvera/walidatora/role_covers, dopisywanie
dopuszczeń do ról, nowe uprawnienia historii, refaktor, zmiana kategorii
innych reguł, nowe mechanizmy eksportu/finalizacji, zmiana danych użytkownika.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: rota/application/deviation_mapping.py --symbol category_for_rule
- REASON: potwierdzić istniejących konsumentów zmienianego mapowania bez drugiego ownera i ogólnego fallbacku.

Po zamrożeniu zakresu implementer/audytor implementacji uruchamia
`python where.py rota/application/deviation_mapping.py` oraz wariant
`--symbol category_for_rule`; dowód czytać przed wnioskami. Nie uruchamiać
mapy podczas samego prechecku briefu.

TASK_SCOPE:
- tasks/ROTA-UNMAPPED-DEVIATION-RULES/brief.md
- tasks/ROTA-UNMAPPED-DEVIATION-RULES/repo_before.hash
- tasks/ROTA-UNMAPPED-DEVIATION-RULES/round_01/
- rota/application/deviation_mapping.py
- tests/test_role_deviation_mapping.py

KONIEC TASK_SCOPE.

## 6. Przekazanie

Niezależny precheck Codexa: jednoznaczność, źródła, testowalność i minimalność
tej korekty. Następnie ocena merytoryczna CC; obie bramy przed implementacją.
Po dostawie niezależny audyt exact SHA, nowy raport
`round_01/tests/tests_r<n>.txt`, bez nadpisywania historii. Merge tylko OWNER.
W BOARD zachować informację, że cztery pozostałe kody nadal wymagają osobnego
rozstrzygnięcia i nie zostały naprawione tym Taskiem.
