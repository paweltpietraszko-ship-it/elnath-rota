# Odpowiedź Codexa — evaluator po ROTA-T044

Status: **OPINIA DO DYSKUSJI — NIE BRIEF, NIE KONTRAKT, ZERO ZMIAN KODU**

Data: 2026-08-31  
Dokument źródłowy: `arch/REQUEST_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `1fd7817`

## Wniosek

Luka jest realna: Symulator zapisuje prawdziwe wyniki, ale nikt ich potem
systematycznie nie czyta. Nie należy jednak budować drugiego dużego systemu.

Rekomenduję pierwszą wersję jako **lokalne, ręcznie uruchamiane dwa kroki**:

1. mały skrypt czyta świeże raporty Wariantu B i przygotowuje jedną zwartą
   paczkę do oceny;
2. Codex/ChatGPT dostaje tę paczkę w bieżącej sesji i zapisuje krótką ocenę.

Skrypt nie łączy się sam z API modelu, niczego nie wysyła, nie poprawia grafiku,
nie tworzy Tasku i nie powtarza `validate()` ani `rota/balance.py`.

## 1. Kiedy i jak evaluator dostaje dane

### Stan obecny

Raporty `reports/**` są lokalne i niecommitowane. To jest dobre dla masowych,
efemerycznych danych, ale oznacza, że nie wolno odkładać oceny „na kiedyś” bez
zachowania kontekstu przebiegu.

### Propozycja

Pierwsza wersja działa **na tym samym komputerze, bezpośrednio po Symulatorze**.
Użytkownik jawnie wskazuje katalog wejściowy. Skrypt tworzy lokalny katalog
jednego przebiegu, np. `evaluations/<run-id>/`, zawierający:

- manifest plików wejściowych;
- exact SHA programu;
- zwartą paczkę dla modelu;
- późniejszą odpowiedź modelu.

Ani surowe raporty, ani cała paczka nie trafiają automatycznie do Git.
Jeżeli ocena wskaże konkretną anomalię, dopiero człowiek promuje wybrany JSON,
reproduktor i krótkie uzasadnienie do osobnego Tasku.

### Korzyść i koszt

Korzyść: brak serwera, bazy, kolejki, chmury, tokenów API i problemu prywatności.
Koszt: ocena wymaga jawnego uruchomienia na tym samym dysku. Na obecnym etapie
to właściwy koszt; trwały magazyn/CI można rozważyć dopiero przy realnej potrzebie
pracy na innym komputerze.

## 2. Zakres wejścia

Pierwsza wersja powinna czytać **wyłącznie completed reports Wariantu B**.

Nie dodawałbym teraz adaptera do Wariantu A:

- ma inny format i inny historyczny cel;
- rozszerza macierz testów bez dowodu, że jest potrzebny;
- może ponownie wprowadzić znane, nierealne założenia dawnych scenariuszy.

Jeśli konkretny failure Wariantu A wymaga oceny, można przekazać go modelowi
ręcznie. Adapter powstaje dopiero po co najmniej jednym rzeczywistym przypadku,
którego ręcznie nie da się obsłużyć.

## 3. Forma wyniku

Evaluator powinien zwracać dwa małe pliki:

- maszynowo czytelny JSON;
- krótki raport po polsku dla OWNERA.

Minimalne kategorie:

- `BRAK_UWAG` — w danych nie znaleziono konkretnej anomalii;
- `DO_SPRAWDZENIA` — istnieje konkretna podejrzana obserwacja;
- `BRAK_DOWODU` — danych nie wystarcza do uczciwej oceny.

Model nie może sam ogłaszać błędu produktu. Każda uwaga musi wskazać:

- run id i seed;
- konkretnych pracowników/dni/zmiany lub status;
- dane, na których opiera ocenę;
- komendę reprodukcji;
- czego nie da się rozstrzygnąć z dostępnych danych.

Wynik czyta najpierw OWNER. Nie ma automatycznego zakładania issue, Tasku,
zmiany kodu ani ponownego uruchamiania solvera.

## 4. Ochrona przed rozrostem i zgadywaniem

Kontrakt evaluatora powinien zawierać pięć twardych zakazów:

1. Nie przeliczaj ponownie zasad, których właścicielem jest `validate()` albo
   `rota/balance.py`; cytuj ich zapisany wynik.
2. Nie poprawiaj wejścia i nie uruchamiaj solvera ponownie.
3. Nie wymyślaj nowych zasad prawa pracy ani polityki firmy.
4. Nie nazywaj obserwacji defektem bez konkretnego reproduktora i wskazanego
   obowiązującego kontraktu; w niepewności użyj `BRAK_DOWODU`.
5. Nie rozszerzaj zakresu o realne dane klientów, Cross-Site, Wariant A,
   automatyczne API LLM ani trwały magazyn bez osobnej decyzji OWNERA.

Skrypt ma wyłącznie wybrać i uporządkować istniejące pola. Jeśli paczka jest za
duża na jedno wywołanie modelu, ma zakończyć się czytelnym komunikatem o limicie,
a nie po cichu obcinać dane lub samodzielnie dzielić je na wiele ocen.

## 5. Ciężar procesu

Nie rekomenduję pełnego procesu tak ciężkiego jak T044.

Wystarczy lekki Task:

1. jedna strona zamrożonego kontraktu wejścia/wyjścia i zakazów;
2. jeden preimplementation reduction gate;
3. mały skrypt pakujący istniejący JSON oraz szablon promptu;
4. trzy celowane próby:
   - zwykły FEASIBLE bez uwag;
   - zapisany podejrzany wynik z konkretną obserwacją;
   - niepełne/za duże dane kończące się `BRAK_DOWODU` albo jawnym błędem;
5. jeden niezależny audyt exact SHA.

Bez adwokata diabła, wielorundowej architektury i pełnej regresji repo, chyba że
w toku pracy pojawi się konkretna zmiana produktu lub wysyłanie danych na zewnątrz.

## Decyzje potrzebne od OWNERA przed briefem

1. Czy akceptujesz lokalny przepływ: Symulator → ręczne uruchomienie skryptu →
   jedna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API?
2. Czy pierwsza wersja ma obsługiwać wyłącznie Wariant B?
3. Czy wynik ma być jedynie rekomendacją `BRAK_UWAG / DO_SPRAWDZENIA /
   BRAK_DOWODU`, bez automatycznego tworzenia Tasków?

Do czasu tych trzech odpowiedzi nie należy pisać briefu ani kodu.
