# ROTA-T021c — frontendowa czarna skrzynka diagnostyczna

Status: **IMPLEMENTED — action-causality contract narrowed per owner ruling
2026-08-24 (round 4 audit)**

Owner decision: Paweł, 2026-08-24 (initial authorization); Paweł, 2026-08-24
(round-4 narrowing of the action-causality guarantee, see §3.2/§3.3 below)

Base branch/SHA: `task/ROTA-T021c` from `713ef5c`

## 0. Granica autoryzacji

Właściciel potwierdził potrzebę automatycznej diagnostyki grubych awarii UI,
np. rozpoznania „system wykrył kliknięcie, ale nie wykrył reakcji”, z
implementacją przez CC i audytem przez Codexa. §3–§5 poniżej to zaakceptowany,
wdrożony kontrakt (nie propozycja) — patrz historia audytu w
`tasks/ROTA-T021c/round_01/tests/tests_r1.txt`…`tests_r4.txt`.

Po trzech rundach audytu §3.2/§3.3 okazały się niewykonalne w pierwotnym,
„gwarantowanym zawsze” brzmieniu — przeglądarka nie daje niezawodnego haczyka
do śledzenia dowolnie opóźnionej pracy asynchronicznej (setTimeout/Promise) z
powrotem do klikniętego elementu; trzy kolejne próby techniczne (opakowanie
`setTimeout`, znakowanie `Promise.reject`, obserwacja mutacji DOM w wąskim
oknie) zawodziły na kolejnych, coraz bardziej wyrafinowanych przypadkach
brzegowych. Właściciel zawęził gwarancję zamiast autoryzować czwartą łatkę —
patrz zmieniona treść §3.2/§3.3.

## 1. Cel

Po grubej awarii UI użytkownik nie ma debugować programu ani opisywać
technikowi całej sekwencji reakcji ekranu. Rota ma sama zachować krótki,
bezpieczny raport pokazujący m.in.:

- co kliknięto;
- czy rozpoczęło się żądanie API albo nawigacja;
- czy wystąpił błąd lub timeout;
- czy po kliknięciu nie zaobserwowano żadnej reakcji;
- na jakim buildzie i ekranie zdarzyła się awaria.

To jest diagnostyka techniczna, nie analityka zachowań użytkowników.

## 2. Istniejące elementy do rozszerzenia

Nie tworzyć równoległych właścicieli:

- wszystkie zwykłe wywołania HTTP przechodzą przez
  `frontend/src/api/client.ts::req`; pobrania przez `downloadPost`;
- korzeń Reacta istnieje w `frontend/src/main.tsx`;
- Workspace ma już przycisk „Pobierz pakiet diagnostyczny”;
- `POST /api/workspace/diagnostics` i
  `rota.application.backup.build_diagnostic_zip` tworzą istniejący ZIP z
  `diagnostics.json` (metadane SQLite bez treści rekordów).

Implementacja ma wykorzystać te punkty. T021c nie może kopiować klienta API,
budować drugiego ekranu diagnostyki ani tworzyć drugiej domenowej ścieżki
backup/diagnostics.

## 3. Zachowanie obowiązkowe

### 3.1 Wspólny rejestr zdarzeń frontu

Jeden wspólny mechanizm utrzymuje ograniczony bufor ostatnich zdarzeń. Każde
zdarzenie ma co najmniej:

- UTC timestamp;
- losowy `session_id`;
- identyfikator buildu/commit SHA (jawne `unknown` jest dozwolone tylko w dev);
- stabilną nazwę ekranu i akcji, bez wartości pól formularza;
- `action_id` łączący kliknięcie z jego dalszym skutkiem, jeśli dotyczy;
- rodzaj zdarzenia i bezpieczne dane techniczne właściwe dla rodzaju.

Wymagane rodzaje:

- `CLICK_RECEIVED`;
- `REQUEST_STARTED`;
- `REQUEST_SUCCEEDED` (status i czas);
- `REQUEST_FAILED` (status albo kategoria błędu i czas);
- `REQUEST_TIMEOUT`;
- `NAVIGATION`;
- `RENDER_ERROR`;
- `UNHANDLED_ERROR`;
- `UNHANDLED_REJECTION`;
- `ACTION_STALLED`;
- opcjonalnie `ACTION_NOOP` dla jawnie obsłużonego, prawidłowego braku zmiany.

Bufor musi przetrwać reload po awarii, ale być ograniczony rozmiarem/liczbą
zdarzeń. Nie jest pełnym dziennikiem aktywności.

### 3.2 Kliknięcie bez reakcji (zawężone przez owner ruling 2026-08-24, runda 4)

Kliknięcia kontrolek interaktywnych są rejestrowane centralnie
(`CLICK_RECEIVED`, zawsze). Rejestr wiarygodnie łączy kliknięcie z jego
`action_id`, gdy skutkiem jest:

- request przez istniejące `req()`;
- nawigacja;
- bezpośredni (synchroniczny) błąd renderowania lub globalny błąd/odrzucenie
  obietnicy, którego pochodzenie da się jednoznacznie ustalić.

Dla pracy dowolnie opóźnionej (np. `setTimeout`, łańcuch obietnic
uruchomiony poza bezpośrednim, synchronicznym wykonaniem handlera kliknięcia)
powiązanie jest best-effort — może wypaść `null`, jeśli pochodzenia nie da się
jednoznacznie ustalić. Niejednoznaczny błąd NIGDY nie „uzdrawia” innego,
niepowiązanego kliknięcia — zamiast tego zostaje bez `action_id`.

Jeżeli w ustalonym, krótkim czasie nie ma żadnego z powyższych (ani jawnego
`ACTION_NOOP`), rejestr zapisuje `ACTION_STALLED` z tym samym `action_id`.
**`ACTION_STALLED` oznacza „nie potwierdzono reakcji”, nie „potwierdzono brak
reakcji”** — to sygnał diagnostyczny typu best-effort, nie dowód. Prawidłowa
akcja nie może być oznaczana jako stalled tylko dlatego, że jej request trwa
dłużej — w takim przypadku obowiązuje osobny timeout requestu.

Implementacja nie może globalnie opakowywać `setTimeout`/`Promise`/innych
mechanizmów przeglądarki w celu pościgu za dowolną asynchronicznością — trzy
kolejne rundy audytu (`tests_r1.txt`–`tests_r3.txt`) pokazały, że to
niewykonalne i tylko przesuwa błąd w inne miejsce.

### 3.3 Awarie i biały ekran

- root React ma globalny ErrorBoundary;
- rejestrowane są także `window.error` i `unhandledrejection` — zawsze, z
  best-effort `action_id` jak w §3.2;
- zamiast białego ekranu użytkownik widzi prosty komunikat, kod diagnostyczny,
  „Pobierz diagnostykę frontu” oraz możliwość bezpiecznego reloadu/powrotu;
- pobranie diagnostyki frontu działa lokalnie nawet wtedy, gdy API nie działa.

Kod diagnostyczny ma pozwolić odnaleźć zdarzenie w raporcie; użytkownik nie ma
kopiować stack trace ani otwierać narzędzi deweloperskich.

### 3.4 Pakiet diagnostyczny

- eksport frontu jest czytelnym JSON-em zawierającym wersję schematu raportu,
  dane buildu/sesji i ograniczony bufor zdarzeń;
- istniejący przycisk „Pobierz pakiet diagnostyczny” nadal zwraca poprawny ZIP
  z dotychczasowym `diagnostics.json` i dodatkowo dołącza aktualną diagnostykę
  frontu, gdy frontend jest dostępny;
- awaria dołączenia frontowego logu nie może zablokować pobrania dotychczasowej
  diagnostyki backendu;
- brak nowej tabeli, migracji albo trwałego dziennika zdarzeń w bazie Roty.

CC wybiera minimalny sposób przekazania bieżącego bufora do istniejącego
downloadu. Nie wolno w tym celu zmieniać reguł domenowych.

### 3.5 Prywatność i lokalność

Raport nie może zawierać:

- nazwisk ani wartości wpisywanych w formularze;
- treści nieobecności/notatek;
- request/response body;
- nagłówków autoryzacyjnych, tokenów, cookies ani sekretów;
- pełnych URL-i/query z identyfikatorami pracowników lub obiektów.

Dozwolone są stabilne nazwy ekranów/akcji, szablon endpointu, metoda HTTP,
status, czas, typ wyjątku i oczyszczona informacja techniczna. Żadne zdarzenia
nie są wysyłane poza lokalną aplikację/API. Brak telemetrii chmurowej.

## 4. Granice zadania

Dozwolone:

- `frontend/**`;
- cienkie zmiany `api/**` potrzebne do istniejącego pobrania diagnostyki;
- testy i konfiguracja rzeczywistych testów przeglądarkowych;
- minimalna zmiana istniejącego buildera ZIP tylko wtedy, gdy nie powiela jego
  odpowiedzialności i nie zmienia zawartości dotychczasowego
  `diagnostics.json`.

Poza zakresem:

- reguły planowania, solver, nieobecności, obsada i inne zachowanie biznesowe;
- nowy ekran administracyjny/analityczny;
- nowe tabele, migracje i repozytoria;
- zewnętrzny monitoring, konta, chmura lub telemetry SDK;
- logowanie każdego stanu komponentu i pełnej historii użytkownika;
- wizualny redesign istniejących ekranów.

## 5. Minimalna macierz akceptacji

Testy muszą uruchamiać rzeczywisty frontend w przeglądarce. Testy źródłowe,
sam build i bezpośrednie wywołania funkcji nie zastępują tej macierzy.

1. Błąd podczas renderowania → nie ma białego ekranu; jest kod i lokalny
   eksport; raport zawiera `RENDER_ERROR`.
2. `window.error` oraz `unhandledrejection` → każde daje właściwe zdarzenie.
3. API 500/network failure → klik, start requestu i `REQUEST_FAILED` mają ten
   sam `action_id`.
4. Wiszący request → `REQUEST_TIMEOUT`, bez fałszywego `ACTION_STALLED`.
5. Kontrolka bez handlera/skutku → `ACTION_STALLED`.
6. Prawidłowa akcja lokalna bez API i prawidłowa akcja z API → brak fałszywego
   stalled.
7. Reload po awarii → poprzednie zdarzenia nadal są w ograniczonym buforze.
8. Istniejący ZIP pozostaje otwieralny i zachowuje `diagnostics.json`; zawiera
   również bieżący raport frontu.
9. Niedostępne API → lokalny eksport frontu nadal działa.
10. Canary privacy test umieszcza charakterystyczne nazwisko, treść formularza,
    token i ID w obsługiwanej ścieżce; żadna z tych wartości nie występuje w
    żadnym eksporcie.
11. Pełna regresja Roty: brak nowych niepowiązanych awarii.

## 6. Delivery dla Codexa

CC przekazuje:

- branch `task/ROTA-T021c` i exact implementation SHA;
- listę zmienionych plików;
- surowy wynik testów przeglądarkowych i pełnej regresji;
- krótki opis sposobu celowego wywołania pięciu klas awarii z §5.

Codex audytuje wyłącznie ten kontrakt. Propozycje szerszej telemetrii lub
przebudowy aplikacji nie są defektami T021c i nie mogą blokować PASS.
