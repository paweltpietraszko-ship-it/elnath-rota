# TOOL-AGENT-PEERS-WINDOWS — sprawdzenie komunikacji Claude Code ↔ Codex na Windows

Status: **READY FOR INDEPENDENT FEASIBILITY AUDIT — READ-ONLY — BEZ INSTALACJI I BEZ IMPLEMENTACJI**

Repozytorium projektu bazowego:

- `Elnath Rota` base: `main@29984801cffcc4f21ed8bf133ad1732816d34826`;
- upstream: `https://github.com/Co-Messi/agent-peers-mcp`;
- dokładny audytowany upstream HEAD: `dc81db4dbe9b3ddb97d3ba64fd24d5b743ef868b`;
- licencja upstream: MIT — wykonawca ma potwierdzić ją z pliku `LICENSE` na
  powyższym SHA.

Ten dokument zleca wyłącznie sprawdzenie wykonalności. Nie zezwala jeszcze na
instalację, zmianę konfiguracji użytkownika, napisanie portu Windows ani
podłączenie prawdziwych sesji.

## 1. Cel zwykłym językiem

Paweł pracuje na natywnym Windowsie. Claude Code i Codex są uruchamiane w
osobnych oknach `cmd`. Obecna sesja Claude Code jest dostępna również z
telefonu, więc gdy potrzebna jest decyzja Pawła, Claude Code może pokazać mu
pytanie bez ręcznego przeklejania wiadomości.

Trzeba sprawdzić, czy istniejący projekt `agent-peers-mcp` można bezpiecznie
uruchomić w tym środowisku tak, aby:

1. Claude Code i Codex mogły wysyłać sobie krótkie wiadomości o pracy;
2. wiadomość budziła właściwą, istniejącą sesję, zamiast tworzyć świeżą sesję
   bez historii rozmowy;
3. ważne decyzje nadal pochodziły wyłącznie od Pawła;
4. `BOARD.md` pozostał technicznym dziennikiem przekazania, a brief danego
   zadania jedynym trwałym źródłem ustaleń produktowych;
5. narzędzie działało lokalnie i nie wprowadzało zmian do kodu programu
   Elnath Rota.

## 2. Zamrożone decyzje OWNER

### OWNER-PEERS-01 — zachowanie kontekstu

Automatyczna wiadomość ma trafić do dokładnie wskazanej, dotychczasowej sesji
Claude Code albo Codexa. Nie wolno uznać uruchomienia świeżej sesji, która zna
tylko pliki repozytorium, za równoważne rozwiązanie.

Jeżeli dana platforma technicznie nie pozwala bezpiecznie dopisać wiadomości do
tej samej sesji, audyt ma to jawnie wykazać. Nie wolno ukrywać utraty kontekstu
przez automatyczne tworzenie długiego promptu zastępczego.

### OWNER-PEERS-02 — decyzje Pawła

Modele mogą przekazywać ustalenia techniczne, wyniki testów i pytania. Nie mogą
przekazywać sobie uprawnienia do zatwierdzania nowego zachowania programu.

Gdy Codex potrzebuje decyzji właściciela:

1. zatrzymuje pracę zgodnie z `OWNER_EXPLANATION_GATE`;
2. zapisuje `OWNER_DECISION_NEEDED` w `BOARD.md`;
3. wysyła do bieżącej sesji Claude Code krótkie pytanie dla Pawła;
4. Claude Code pokazuje je Pawłowi w sesji dostępnej z telefonu;
5. praca może ruszyć dalej dopiero po odpowiedzi Pawła zapisanej w kontrakcie
   danego Tasku jako `OWNER_ACCEPTED` albo `OWNER_CORRECTED`.

Sama wiadomość Claude Code, Codexa, brokera lub watchera nigdy nie jest decyzją
OWNER.

### OWNER-PEERS-03 — brak samodzielnego projektowania

Automatyzacja ma tylko dostarczać wiadomości i budzić właściwą sesję. Nie może:

- sama tworzyć nowych Tasków;
- rozszerzać zakresu istniejącego Tasku;
- automatycznie akceptować poprawek;
- scalać gałęzi;
- uruchamiać nieskończonej rozmowy modeli;
- omijać bramek bezpieczeństwa, sandboxa ani zgód użytkownika.

### OWNER-PEERS-04 — Windows i bieżące narzędzia

Docelowe środowisko to natywny Windows oraz `cmd`, bez obowiązkowego WSL,
`tmux` ani osobnej maszyny Linux. Należy zachować obecne instalacje i
uwierzytelnienie Claude Code oraz Codexa. Dodatkowy klucz API nie może być
wymagany do podstawowej wymiany wiadomości.

## 3. Pytania, na które audyt ma odpowiedzieć

Audytor ma odpowiedzieć dowodami `plik:linia` z upstream SHA na każde pytanie:

1. Które elementy upstream już działają na natywnym Windowsie bez zmian?
2. Które elementy są wyłącznie uniksowe i dlaczego?
3. Czy problem ogranicza się do cienkiej warstwy uruchamiania Windows, czy
   dotyka protokołu wiadomości, brokera albo trwałości sesji?
4. Czy `Bun`, SQLite, lokalny broker HTTP i oba serwery MCP są przenośne bez
   zmiany ich znaczenia?
5. Jak upstream realizuje prawa `0600/0700`, sygnały, PID, odłączony daemon,
   ścieżki `~`, symlinki, terminal/TTY i blokadę jednego autora sesji? Co jest
   odpowiednikiem na Windows?
6. Czy `wakeable Codex` naprawdę używa tego samego `thread_id`, historii i
   katalogu roboczego przez oficjalny `codex app-server`?
7. Czy wiadomość może trafić do już uruchomionej zwykłym poleceniem sesji, czy
   sesję trzeba od początku uruchomić przez wrapper upstream?
8. Czy bieżąca sesja Claude Code dostępna z telefonu zachowuje to połączenie,
   gdy zostanie uruchomiona przez wymagany wrapper?
9. Co dzieje się, gdy adresat jest zajęty, zamknięty, ponownie uruchomiony albo
   ma nieodebraną wcześniejszą wiadomość?
10. Jak rozwiązanie zapobiega duplikatom, złemu adresatowi, równoczesnemu
    zapisowi do jednej sesji i nieskończonemu ping-pongowi?
11. Jakie dane są zapisywane lokalnie, jak długo, z jakimi prawami dostępu i
    czy cokolwiek jest wysyłane poza komputer bez jawnej zgody?
12. Czy aktualizacja upstream może zmienić zachowanie bez naszej kontroli i
    jak przypiąć używaną wersję?

## 4. Dozwolony sposób sprawdzenia

Audytor może:

- sklonować dokładny upstream SHA do jednorazowego katalogu w `%TEMP%`;
- czytać cały kod, dokumentację, testy i historię potrzebną do wyjaśnienia
  wskazanego SHA;
- uruchomić istniejące testy upstream w odizolowanym klonie;
- wykonać małe, jednorazowe reproduktory na `localhost`, jeżeli nie zmieniają
  konfiguracji prawdziwych klientów;
- sprawdzić wersje już zainstalowanych `cmd`, PowerShell, Bun, Claude Code i
  Codexa, ale nie aktualizować ich;
- porównać użyte API Codexa z oficjalnym interfejsem `app-server`.

Przed każdym reproduktorem raport ma podać, jakie pliki/procesy/porty zostaną
utworzone i jak zostaną usunięte. Nie wolno używać prawdziwego repozytorium
Elnath Rota jako poligonu dla brokera.

## 5. Zakres zabroniony

W tej fazie nie wolno:

- zmieniać `~/.codex/config.toml`, `~/.claude.json`, ustawień aplikacji ani
  autostartu Windows;
- instalować MCP do prawdziwej sesji Claude Code lub Codexa;
- wysyłać wiadomości do obecnych sesji Pawła;
- modyfikować, kopiować ani refaktoryzować kodu produktu Elnath Rota;
- tworzyć naszego brokera, watchera albo protokołu wiadomości;
- forkować upstream i pisać poprawki Windows;
- uruchamiać z flagami omijającymi sandbox lub zgody;
- wystawiać lokalnego brokera poza `127.0.0.1`;
- używać płatnego API albo przesyłać treści projektu do zewnętrznego modelu;
- zgłaszać issue albo PR do upstream bez osobnej zgody Pawła.

Jeżeli rzetelna odpowiedź wymaga którejkolwiek z tych czynności, audytor ma
zatrzymać się i wyjaśnić potrzebę zwykłym językiem.

## 6. Minimalna macierz dowodowa

### F01 — źródło i licencja

- dokładny checkout ma SHA `dc81db4dbe9b3ddb97d3ba64fd24d5b743ef868b`;
- plik `LICENSE` pozwala na lokalną modyfikację i dystrybucję forka;
- raport wskazuje, które pliki i informacje licencyjne trzeba zachować.

### F02 — statyczna mapa Windows

Tabela wszystkich rzeczywistych zależności systemowych z klasyfikacją:

- `PORTABLE` — działa bez zmiany znaczenia;
- `WINDOWS_ADAPTER` — wymaga cienkiego odpowiednika Windows;
- `FORK_LOGIC` — wymaga zmiany logiki upstream;
- `UNPROVEN` — brak wystarczającego dowodu.

Samo wystąpienie znaku `/` albo `~` nie jest dowodem nieprzenośności.

### F03 — testy upstream na Windows

- uruchomiona pełna istniejąca suita upstream na przypiętym SHA;
- każda porażka sklasyfikowana według rzeczywistej przyczyny;
- brak poprawiania testów tylko po to, aby były zielone.

### F04 — broker bez prawdziwych klientów

W izolowanym katalogu i na jednorazowym porcie:

- start i zatrzymanie brokera;
- zapis jednej wiadomości;
- odczyt, potwierdzenie i brak ponownego uznania jej za nową;
- zachowanie niepotwierdzonej wiadomości po kontrolowanym restarcie;
- brak nasłuchiwania poza loopbackiem.

Jeżeli upstreamowe testy już dowodzą całej tej klasy na Windowsie, nie należy
powielać jej drugim dużym testem.

### F05 — ciągłość sesji bez podłączania prawdziwego konta

Kod i istniejące testy mają dowieść albo obalić, że:

- przechowywany jest konkretny identyfikator sesji/wątku;
- wake dotyczy tylko stanu idle;
- nie tworzy się zapasowy świeży wątek po niejednoznacznym błędzie;
- ponowienie nie uruchamia dwóch autorów tego samego wątku;
- kontekst rozmowy pozostaje historią tego samego wątku.

Jeśli nie da się tego uczciwie sprawdzić bez prawdziwej sesji, wynik ma być
`UNPROVEN` i ma opisywać najmniejszy późniejszy test integracyjny. W tej fazie
nie wolno go wykonywać.

### F06 — ścieżka OWNER

Audyt ma rozpisać mechaniczny przebieg:

`Codex -> OWNER_DECISION_NEEDED -> Claude Code -> telefon Pawła -> zapis decyzji w briefie -> powiadomienie Codexa`.

Należy wskazać, co zapewnia upstream, a co pozostaje zasadą naszego
`AGENTS.md`/`BOARD.md`. Upstream nie może sam interpretować odpowiedzi jako
decyzji OWNER.

## 7. Oczekiwany wynik

Raport ma wybrać dokładnie jedną klasyfikację:

1. `FEASIBLE_UNCHANGED` — upstream może być użyty na natywnym Windowsie bez
   zmian kodu;
2. `FEASIBLE_THIN_WINDOWS_ADAPTER` — potrzebne są wyłącznie wskazane launchery,
   ścieżki, ACL lub zarządzanie procesem Windows; protokół i broker pozostają
   bez zmian;
3. `FORK_REQUIRED` — potrzebna jest utrzymywana zmiana logiki upstream;
4. `NOT_RECOMMENDED` — rozwiązanie nie może wiarygodnie zachować kontekstu albo
   wymaga zbyt niebezpiecznych/niestabilnych mechanizmów.

Dla wybranej klasy raport ma podać:

- listę konkretnych plików/symboli do późniejszego zakresu;
- elementy upstream, których nie wolno przepisywać;
- ryzyka aktualizacji i bezpieczeństwa;
- najmniejszy późniejszy test na dwóch kontrolowanych sesjach;
- szacowaną liczbę nowych plików naszego adaptera, bez szacowania czasu;
- listę pytań wymagających decyzji Pawła, jeżeli istnieją.

Nie wolno w raporcie zamienić `UNPROVEN` w pozytywną opinię.

## 8. Artefakty i raport

Jedynym trwałym zapisem w repozytorium Elnath Rota ma być:

- `tasks/TOOL-AGENT-PEERS-WINDOWS/round_01/tests/tests_r1.txt`.

Raport musi zawierać:

- exact Elnath base SHA i exact upstream SHA;
- wersje środowiska;
- użyte polecenia;
- wyniki F01–F06;
- dowody `plik:linia`;
- jedną klasyfikację z sekcji 7;
- informację, że nie zmieniono konfiguracji prawdziwego Claude Code/Codexa;
- informację, co utworzono w `%TEMP%` i czy zostało usunięte.

Przed zapisem sprawdzić, że ścieżka raportu nie istnieje. Nie nadpisywać żadnego
wcześniejszego raportu.

## 9. Bramka po raporcie

Raport nie zezwala automatycznie na implementację.

- `FEASIBLE_UNCHANGED` albo `FEASIBLE_THIN_WINDOWS_ADAPTER`: Paweł wybiera, czy
  przechodzimy do kontrolowanego pilota.
- `FORK_REQUIRED`: potrzebna jest osobna decyzja Pawła, czy utrzymywać fork.
- `NOT_RECOMMENDED`: żadnej implementacji bez nowego rozwiązania i nowego
  briefu.

Dopiero po decyzji Pawła powstaje osobny, mały kontrakt implementacyjny z
zamrożonym zakresem. Wtedy należy wykonać `PRE_IMPLEMENTATION_REDUCTION_GATE`.

## 10. Polecenie dla nowej instancji Codexa

> Branch: `docs/agent-peers-windows-feasibility`
>
> Przeczytaj `AGENTS.md`, `BOARD.md` i cały
> `tasks/TOOL-AGENT-PEERS-WINDOWS/brief.md`. Jesteś niezależnym audytorem
> wykonalności, nie implementatorem. Audytuj upstream
> `Co-Messi/agent-peers-mcp` wyłącznie na exact SHA
> `dc81db4dbe9b3ddb97d3ba64fd24d5b743ef868b`. Nie instaluj MCP, nie zmieniaj
> konfiguracji Claude Code ani Codexa i nie podłączaj prawdziwych sesji.
> Wykonaj F01–F06 i zapisz jedyny raport w ścieżce wskazanej w briefie. Nie
> pisz portu Windows. Jeśli do dowodu potrzebna jest czynność zabroniona,
> zatrzymaj się i wyjaśnij ją zwykłym językiem.
