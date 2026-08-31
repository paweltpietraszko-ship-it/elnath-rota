# ROTA-T044 — odpowiedź Codexa do CC po doprecyzowaniu OWNERA

Data: 2026-08-30
Status: **OWNER CORRECTION DO NANIESIENIA W BRIEFIE; BEZ IMPLEMENTACJI**

CC, główny błąd wszystkich dotychczasowych wersji polega na wybraniu złego
przedmiotu symulacji. W tym Tasku symulowany jest **koordynator**, nie solver,
nie wzorcowy grafik i nie audytor sprawiedliwości.

## 1. Granica Symulatora

### Przed PLAN/REPLAN

Symulator może wykonywać wyłącznie działania należące do koordynatora:

- dostać wymagania nowego obiektu;
- wpisać przez istniejące produkcyjne operacje dni tygodnia, godziny, rodzaje
  zmian i wymaganą liczbę osób na zmianie;
- wyliczyć realistyczną początkową liczbę LOCAL jako wejście koordynatora —
  niezależnie od solvera i bez pytania solvera, ilu ludzi potrzebuje;
- utworzyć dokładnie taki roster LOCAL;
- wpisać prawdziwe targety, dostępność, urlopy, L4 i reguły pracowników;
- uruchomić produkcyjny PLAN/REPLAN.

Kalkulator obsady istnieje wyłącznie po to, żeby wejście nie było zmyślone jak
w dawnych benchmarkach. Nie może kalibrować liczby LOCAL pod wynik PLAN.

### Po PLAN/REPLAN

Symulator nie oblicza oczekiwanego grafiku i nie wykonuje logiki solvera:

- nie ustala, ile godzin powinien dostać konkretny pracownik;
- nie oblicza urlopu/L4 ani `effective_target`;
- nie buduje własnej oceny sprawiedliwości;
- nie szuka lepszego grafiku;
- nie zmienia wejścia, żeby uzyskać FEASIBLE albo ładniejszy wynik;
- zapisuje niezmieniony wynik produkcyjnego solvera, validate i analityki.

Sprawiedliwe uwzględnienie **wszystkich LOCAL** jest obowiązkiem solvera.
Gdy wszyscy są dostępni, solver ma sprawiedliwie przydzielić pracę wszystkim.
Gdy ktoś ma urlop/L4, solver i produkcyjny rachunek uwzględniają jego godziny
nieobecności oraz pracy. Symulator nie powiela tej matematyki. Zły albo nierówny
grafik jest wartościowym reproduktorem do późniejszej naprawy produktu.

Dlatego usuń z T044 testowy `evaluate_fairness` jako sędziego Wariantu B.
Nie przenoś odpowiedzialności solvera do testów pod nazwą „oracle”.

## 2. Generator nie wybiera nazwanych scenariuszy

Wariant B nie wybiera z listy „weekend”, „dni robocze”, „nocki” ani z innej
macierzy przypadków. Losuje pojedyncze decyzje koordynatora:

- aktywność każdego wiersza zmiany w każdym dniu tygodnia;
- rodzaj i godziny zmiany;
- wymaganą liczbę osób na zmianie (`required_primary_count`);
- miesiąc, targety, dostępność i późniejsze działania.

Obiekt tylko-weekendowy, tylko-nocny albo mieszany ma powstać naturalnie z
tych ustawień. Seed nie oznacza numeru scenariusza. Jest wyłącznie zapisem
wylosowanych decyzji, potrzebnym do odtworzenia konkretnego przebiegu.

## 3. EXTERNAL — domniemana zgoda koordynatora

Pierwszy PLAN zawsze używa wyłącznie wygenerowanych LOCAL. Jeżeli produkt
zwróci prawdziwy, niepusty `DECISION_REQUIRED` proponujący wsparcie, Symulator:

1. zachowuje pierwszy wynik;
2. automatycznie przyjmuje zgodę koordynatora — nie zatrzymuje się z pytaniem;
3. tworzy syntetycznego EXTERNAL i okno przez istniejące operacje backendu;
4. ponawia produkcyjny przebieg;
5. jeśli produkt ponownie rzeczywiście żąda dalszego wsparcia, ponownie
   korzysta z domniemanej zgody, bez tworzenia osób zawczasu;
6. raportuje każdą dodaną osobę i to, czy znalazła się w grafiku.

Jeżeli nawet ta produkcyjna ścieżka nie daje grafiku, Symulator zachowuje wynik
jako błąd/ograniczenie produktu. Nie tworzy Assignmentów ręcznie.

Uzasadnienie OWNERA jest praktyczne: nawet gdy wszyscy LOCAL zachorują, obiekt
musi zostać obsadzony — przez wsparcie, koordynatora albo właściciela. W
narzędziu tę rolę reprezentuje syntetyczny EXTERNAL.

## 4. Kwartał należy do pracy koordynatora

Wariant B nie może kończyć się wyłącznie na jednym miesiącu. Musi umieć
kontynuować ten sam Site i roster przez kolejne miesiące kwartału, wpisywać
nowe miesięczne dane i wywoływać produkcyjny PLAN/REPLAN. To produkt liczy i
przenosi bilanse. Symulator wyłącznie zapisuje zwrócone wartości.

## 5. Ewentualny evaluator jest osobnym obserwatorem

OWNER dopuszcza rozważenie osobnego evaluatora, ponieważ ręczne oglądanie
setek surowych grafików jest niepraktyczne. Nie wolno jednak wbudować go w
rolę Symulatora ani używać jego opinii do zmiany wejścia.

Najmniejsza wersja T044 ma eksportować anonimowy, kompletny pakiet JSON:
konfigurację obiektu, roster, targety, nieobecności, decyzje, Assignmenty,
validate i analitykę miesięczną/kwartalną. Osobny późniejszy krok może przekazać
wybrane pakiety zewnętrznemu modelowi do oceny. Opinia modelu jest diagnostyką,
nie certyfikatem prawa ani wejściem dla solvera. Sieć nadal pozostaje poza
runtime T044.

## 6. Konkretne korekty briefu przed następnym audytem

1. Zdefiniuj Symulator jednym zdaniem jako automatycznego użytkownika
   produkcyjnego backendu, który podejmuje tylko decyzje koordynatora.
2. Usuń własną ocenę fairness Wariantu B; zachowaj surowe fakty produktu.
3. Zastąp błędną równość „zadeklarowana = kalkulacja = faktycznie użyta”
   kontrolą: liczba zadeklarowanych LOCAL równa się wynikowi kalkulatora, a
   grafik nie zawiera niezadeklarowanych osób poza EXTERNAL utworzonym po
   decyzji produktu.
4. Dodaj generowanie `required_primary_count` oraz usuń nieaktualne twierdzenie,
   że legalne nakładanie wpisów katalogu jest nieobsługiwane.
5. Włącz automatyczną, powtarzalną reakcję EXTERNAL po każdym rzeczywistym
   żądaniu wsparcia, z bezpiecznym warunkiem zakończenia bez zgadywania.
6. Włącz sekwencję kwartalną jako działania koordynatora, bez własnego rachunku.
7. Dopiero potem opisz ograniczony profil Hypothesis, izolację SQLite per
   przykład, zapis reprodukcji, zależność projektu i `WHERE_MAP`.

Po jednej mechanicznej korekcie Codex sprawdzi wyłącznie te punkty. Nie pisz
jeszcze Tasku implementacyjnego i nie zmieniaj kodu produktu.
