# Odpowiedź architekta — evaluator po ROTA-T044

Status: **OPINIA DO DYSKUSJI — NIE BRIEF, NIE KONTRAKT, ZERO ZMIAN KODU**

Data: 2026-08-31

Źródła:

- `arch/REQUEST_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `1fd7817bdbaee840f89e474391e763042e5036f5`;
- `arch/CODEX_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `4cc2652d01c41b8b630fbba889c8eda025d6ea87`.

## Wniosek

Popieram kierunek Codexa. Pierwsza wersja evaluatora powinna być celowo mała i ręczna.

Nie budujemy nowego systemu, który próbuje samodzielnie udowodnić, że grafik jest dobry. Symulator już wykonał swoją pracę: wygenerował realny obiekt, przepuścił go przez prawdziwy backend/solver i zapisał surowy wynik. Evaluator ma ten wynik **przeczytać i wskazać rzeczy, które warto obejrzeć**, a nie poprawiać solver, przeliczać jego reguły albo automatycznie rozpoczynać naprawę produktu.

Przed briefem rekomenduję OWNEROWI potwierdzenie wszystkich trzech decyzji opisanych przez Codexa, z poniższymi doprecyzowaniami.

## DECYZJA 1 — lokalny, ręczny przepływ bez automatycznego API LLM

### Rekomendacja architekta: **TAK**

Pierwsza wersja powinna działać w takim przepływie:

1. Symulator B kończy przebieg i pozostawia lokalne `reports/**`.
2. OWNER/CC jawnie uruchamia mały skrypt pakujący wskazany świeży przebieg.
3. Skrypt tworzy lokalną, deterministyczną paczkę oceny oraz manifest źródeł.
4. OWNER jawnie przekazuje tę paczkę do bieżącej sesji Codexa/ChatGPT.
5. Model zwraca ocenę według zamrożonego formatu.
6. Dopiero człowiek decyduje, czy konkretne znalezisko zasługuje na promocję do repo / osobnego Tasku.

Nie rekomenduję w v1:

- automatycznego wywoływania API LLM;
- kolejki/background workera;
- serwera lub trwałej bazy evaluacji;
- automatycznego wysyłania `reports/**` gdziekolwiek;
- commitowania wszystkich surowych raportów;
- automatycznego wybierania kolejnego Tasku.

### Ważne doprecyzowanie

„Zaraz po Symulatorze” nie musi znaczyć „w tym samym procesie Pythona”. Ma znaczyć: **na tym samym lokalnym zbiorze raportów, zanim zostanie on usunięty lub nadpisany**.

Packager powinien utrwalić co najmniej:

- listę dokładnych plików źródłowych;
- ich identyfikatory/nazwy i — jeśli technicznie tanie — checksumy;
- exact SHA kodu, na którym powstały raporty, jeżeli informacja jest dostępna;
- gotową paczkę danych dla modelu;
- wersję/formę promptu używanego do oceny.

Celem jest możliwość odpowiedzi na pytanie: „z jakich dokładnie danych powstała ta opinia?”, bez tworzenia nowej infrastruktury.

## DECYZJA 2 — pierwsza wersja wyłącznie dla Wariantu B

### Rekomendacja architekta: **TAK**

V1 powinna czytać wyłącznie completed reports Wariantu B.

Powody:

- T044 został właśnie zamknięty merytorycznie i jego raw-report jest świadomie przygotowany pod downstream analizę;
- format B zawiera obiekt, roster, absencje, PLAN/EXTERNAL/REPLAN, candidates/Assignments oraz `readback.analytics`/`readback.month_view`;
- Wariant A ma inny historyczny cel i inny format;
- dodanie A teraz nie poprawia jakości oceny B, tylko zwiększa liczbę adapterów i przypadków brzegowych.

Nie oznacza to decyzji „Wariant A nigdy”. Oznacza tylko: **nie projektujemy adaptera bez rzeczywistego przypadku, który go wymaga**.

Failure JSON-y harnessu również nie powinny być głównym wejściem evaluatora jakości grafiku. Jeżeli Symulator sam się wywrócił, najpierw naprawiamy/diagnozujemy harness. Evaluator ma przede wszystkim czytać poprawnie zakończone, surowe wyniki produktu.

## DECYZJA 3 — wynik jako rekomendacja, bez automatycznego Tasku

### Rekomendacja architekta: **TAK**

Popieram trzy kategorie:

- `BRAK_UWAG`;
- `DO_SPRAWDZENIA`;
- `BRAK_DOWODU`.

Ale ich znaczenie musi być bardzo precyzyjne.

### `BRAK_UWAG`

Nie znaczy:

> „grafik jest poprawny” albo „solver ma PASS”.

Znaczy wyłącznie:

> „w dostarczonym zestawie danych evaluator nie znalazł konkretnej obserwacji, którą potrafi uczciwie uzasadnić”.

To ważne, bo LLM nie jest formalnym dowodem poprawności.

### `DO_SPRAWDZENIA`

Może być użyte tylko wtedy, gdy evaluator potrafi wskazać konkretnie:

- run/seed;
- pracownika/pracowników;
- dzień/dni lub zmianę/zmiany;
- obserwowane dane;
- dlaczego układ wygląda podejrzanie;
- co już mówi zapisany `validate()` / analytics / balance, jeśli to istotne;
- komendę reprodukcji;
- czego evaluator **nie wie** i czego nie może rozstrzygnąć.

Nie wolno automatycznie zamieniać `DO_SPRAWDZENIA` w `DEFECT`.

### `BRAK_DOWODU`

Stosujemy, gdy dane są poprawnie zbudowaną paczką, ale nie wystarczają do uczciwej oceny obserwacji.

Natomiast uszkodzona paczka, brak wymaganych pól, nieczytelny JSON albo przekroczony twardy limit wejścia powinny być **błędem narzędzia/pakowania**, a nie `BRAK_DOWODU`. Inaczej techniczna awaria packagera zacznie wyglądać jak merytoryczna opinia o grafiku.

## Dodatkowa granica — czego modelowi wolno szukać

Evaluator jakościowy powinien szukać przede wszystkim **anomalii widocznych w gotowym grafiku**, np. wzorców, które dla człowieka wyglądają podejrzanie i zasługują na sprawdzenie.

Nie powinien:

- przeliczać ponownie HARD rules;
- implementować własnego odpowiednika `validate()`;
- przeliczać od zera bilansów, których ownerem jest produkt;
- uruchamiać solvera ponownie;
- zmieniać wejścia;
- tworzyć „lepszego grafiku” dla porównania;
- wymyślać prawa pracy lub polityki firmy, których nie ma w kontrakcie;
- na podstawie samego wrażenia twierdzić, że istnieje defekt.

Jeżeli np. rozkład godzin wygląda nierówno, model może powiedzieć „to warto sprawdzić” i pokazać dane. Nie może sam dopisać reguły typu „różnica > X godzin jest błędem”, jeśli produkt/OWNER nigdy takiej granicy nie ustalił.

## Propozycja minimalnego podziału odpowiedzialności

### Skrypt/packager — deterministyczny

Ma tylko:

- znaleźć wskazane completed reports B;
- sprawdzić, że mają wymagany minimalny shape;
- uporządkować/pomniejszyć reprezentację **bez utraty faktów potrzebnych do oceny**;
- dołączyć manifest i reprodukcję;
- przygotować jeden jawny input dla modelu.

Nie ma wydawać opinii o grafiku.

### Codex/ChatGPT — jakościowy evaluator

Ma:

- czytać paczkę jako materiał dowodowy;
- odróżniać zapisane fakty produktu od własnej interpretacji;
- wskazywać konkretne anomalie;
- używać tylko trzech wyników powyżej;
- nie tworzyć Tasków ani zmian w repo samodzielnie.

### OWNER — gate decyzyjny

OWNER decyduje, czy `DO_SPRAWDZENIA`:

- odrzucić jako akceptowalny wynik;
- poprosić o reprodukcję/dodatkowy audyt;
- przekształcić w osobny Task naprawczy.

## Proces dla przyszłego Tasku

Nie rekomenduję powtarzania ciężaru T044.

Jeżeli OWNER potwierdzi trzy decyzje, następny Task może być mały, ale powinien mieć zwykłe zabezpieczenia przed rozszerzeniem zakresu:

- krótki frozen input/output contract;
- PRE_IMPLEMENTATION_REDUCTION_GATE;
- `WHERE_MAP` tylko jeżeli implementacja dotknie istniejących ownerów raportowania/formatu B;
- trzy-cztery celowane przypadki;
- niezależny exact-SHA audit;
- zero pełnej regresji bez realnej potrzeby.

Nie widzę potrzeby adwokata diabła na starcie, o ile Task pozostanie packagerem + szablonem oceny i nie zacznie implementować własnej logiki jakościowej.

## Rekomendacja do OWNERA w jednym zdaniu

**Potwierdziłbym wszystkie trzy decyzje Codexa: lokalnie i ręcznie, tylko Wariant B, wynik wyłącznie rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego API i bez automatycznego tworzenia Tasków.**

Po takim potwierdzeniu można napisać mały brief; przed nim nie widzę potrzeby kolejnych decyzji produktowych.