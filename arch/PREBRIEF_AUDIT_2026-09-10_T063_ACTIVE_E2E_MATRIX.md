# ROTA-T063 — pre-brief audit aktywnej macierzy E2E

Stan sprawdzony statycznie na `main@2307eaa`. Nie uruchamiano testów i nie używano
zamrożonych Symulatorów A/B ani benchmarków.

## Wniosek

T063 jest gotowe do briefu jako **zadanie jakości testów**, bez zmiany zachowania
produktu. Nie jest prawdą, że repo nie ma żadnego realnego pionu. Ma jeden test,
który dochodzi od konfiguracji przez prawdziwy PLAN do widocznej, niepustej
służby. Brakuje natomiast stabilnej i jawnie nazwanej macierzy akceptacyjnej,
która odróżnia „program rzeczywiście ułożył grafik” od „ekran poprawnie obsłużył
dowolny status backendu”.

**OWNER_RULING 2026-09-10:** celem T063 jest, aby testy dowodziły rzeczywistego
wyniku biznesowego programu, a nie jedynie tego, że API odpowiedziało i frontend
wyświetlił zwrócony status. Zielony test pionowy musi wykazać z góry określony
rezultat: dla scenariusza dodatniego powstał niepusty grafik ze służbami
widocznymi dla koordynatora; dla scenariusza ujemnego PLAN zatrzymał się z
konkretnie oczekiwanej przyczyny.

**OWNER_RULING 2026-09-10 — absencje i wsparcie zewnętrzne:** urlop, choroba i
nagła absencja są zwykłą rzeczywistością obiektu i T063 ma je obejmować.
Koordynator ręcznie wpisuje konkretne osoby wsparcia zewnętrznego; teoretycznie
każdą służbę może wykonywać inna osoba. Solver nie może tworzyć osób ani
traktować wsparcia jako anonimowej, nieskończonej puli. Może używać wyłącznie
osób rzeczywiście wpisanych przez koordynatora i dla każdej z nich nadal musi
respektować wszystkie HARD, w tym odpoczynek i dostępność. Jeżeli pierwsza osoba
zewnętrzna nie może objąć kolejnej służby z powodu HARD, solver ma użyć innej
wpisanej i dostępnej osoby; nie wolno mu złamać HARD. Oczekiwanym realnym
procesem jest uzupełnienie obsady i stworzenie pełnego grafiku. Brak możliwości
ułożenia grafiku pozostaje dopuszczalną możliwością teoretyczną, a nie domyślnym
wynikiem niedoboru lokalnej załogi.

## Fakty z aktywnego `frontend/e2e/**`

Jedenaście testów w pięciu plikach uruchamia prawdziwy PLAN przez przeglądarkę i
realny backend:

- siedem korzysta z pustego katalogu zmian, czyli solver rozwiązuje przypadek
  bez zapotrzebowania i bez realnych służb;
- jeden celowo tworzy zapotrzebowanie bez pracowników i deterministycznie
  sprawdza `DECISION_REQUIRED`;
- trzy testy T041 zapisują jedną dzienną zmianę 06:00–18:00 i pięciu LOCAL;
  tworzą prawdziwy grafik;
- tylko `t041-daily-workflow.spec.ts::C06` następnie wskazuje rzeczywistą komórkę
  służby, zatwierdza grafik, wykonuje korektę i sprawdza zachowanie wersji;
- żaden aktywny E2E nie dowodzi dodatniego, całodobowego D+N dla całego miesiąca.

`t043-coordinator-confidence.spec.ts` jest mylący jako dowód jakości solvera:
tworzy pięciu LOCAL, ale nie zapisuje katalogu zmian. PLAN ma więc zerowe
zapotrzebowanie. Dodatkowo test akceptuje zamiennie `FEASIBLE` i
`DECISION_REQUIRED`; potwierdza tylko, że ekran powtórzył odpowiedź API.

## Izolacja i wiarygodność

- `global-setup.ts` nie czyści dedykowanej bazy E2E; jedynie dopisuje
  koordynatora. Dane pozostają między uruchomieniami.
- `t054-independent-audit.spec.ts` wykonuje nieskopowane `UPDATE` wszystkich
  podglądów i tworzy trwały trigger SQLite bez sprzątania. To może wpływać na
  późniejsze testy lub ponowne uruchomienie.
- konfiguracja Playwright ma dwa ponowienia, które mają przykrywać znany wyścig
  połączenia SQLite. Ponowienie nie może być dowodem poprawności ścieżki
  akceptacyjnej; raport ma odróżniać awarię infrastruktury od wyniku produktu.
- zależność generatora kalendarza od rzeczywistego bieżącego miesiąca należy do
  T064. T063 nie może jej maskować podrobieniem daty. Deterministyczny miesiąc
  przez prawdziwy interfejs wymaga wcześniejszego T064 albo jawnej zależności od
  niego.

## Granice briefu T063

1. Zakres testowy; bez zmian produkcyjnych. Odkryty błąd produktu trafia do
   osobnego findingu, a nie jest naprawiany przy okazji.
2. Zachować testy mechaniki ekranów tam, gdzie są przydatne, lecz nie nazywać
   pustego PLANU dowodem ułożenia grafiku.
3. Poprawić albo przeklasyfikować T043: wynik musi być z góry określony, bez
   alternatywy „FEASIBLE lub DECISION_REQUIRED”. Samo porównanie odpowiedzi API
   z napisem na ekranie nie spełnia celu T063.
4. Dodać jawne scenariusze akceptacyjne, zbudowane wyłącznie
   przez normalne operacje koordynatora:
   - dodatni: istniejący, OWNER-zaakceptowany prosty obiekt D/N 12 h, jedna
     pełna warstwa i pięciu LOCAL; PLAN musi zwrócić `FEASIBLE`, kandydat ma
     zostać wybrany, na ekranie muszą być widoczne rzeczywiste służby, a wynik
     ma przetrwać odświeżenie;
   - absencja i wsparcie: po realnej absencji koordynator wpisuje konkretne
     osoby zewnętrzne, każda podlega HARD, a ponowne planowanie ma obsadzić
     służby, o ile wpisany zestaw faktycznie wystarcza;
   - ujemny przypadek technicznie dopuszczalny: jeżeli jawnie wpisana obsada
     lokalna i zewnętrzna naprawdę nie wystarcza, test oczekuje konkretnego
     zatrzymania, nigdy złamania HARD ani stworzenia niewpisanej osoby.
5. Każdy przebieg zaczyna się od czystej, dedykowanej bazy albo równoważnej
   pełnej izolacji. Żaden test nie zmienia wszystkich rekordów ani nie zostawia
   triggera dla kolejnych testów.
6. T063 nie wymyśla losowych lub „maksymalnych” edge case. Dalsze scenariusze
   wymagają realnego przykładu zaakceptowanego przez OWNERA.
7. Końcowy dowód dodatniego scenariusza obejmuje zapisany zrzut widocznego
   grafiku oraz wygenerowany PDF do oceny optycznej. Zielona asercja danych nie
   zastępuje oceny wydruku.

## Zależności

- T062 może dostarczyć docelową treść i akcję po zatrzymanym PLANIE; T063 nie
  projektuje jej ponownie.
- T064 powinno dostarczyć wybór/generowanie jawnego miesiąca. Jeżeli brief T063
  powstanie wcześniej, ma zawierać zależność wykonawczą od T064 zamiast
  utrwalać obejście z zegarem przeglądarki.
