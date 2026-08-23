# T021 Screen 2 — Ogólna dostępność / rozstrzygnięcie architekta

STATUS: RESOLVED — MULTIPLE INDEPENDENT `UNAVAILABLE_24H` PERIODS
INPUT_SHA: `ac863c71989d591e2f7435d6fde57d10ea3bc543`
DATE: 2026-08-23

## ROZSTRZYGNIĘCIE

„Ogólna dostępność” **nie ma jednej globalnej/current/future rodziny na pracownika**.

Jeden pracownik może mieć wiele niezależnych rodzin `AvailabilityKind.UNAVAILABLE_24H`, każda identyfikowana własnym `availability_id` i własnym zakresem `start_date..end_date`.

Nie dodawać invariant „maksymalnie jeden aktualny/przyszły UNAVAILABLE_24H”, nie scalać rodzin i nie wybierać „tej właściwej” przez lookup+branching. Istniejący model Availability jest już wielorodzinny i nie ma produktu wymagającego sztucznej pojedynczości.

## KONSEKWENCJE DLA SCREEN 2

1. **Nowy okres** Ogólnej niedostępności tworzy nową rodzinę z nowym, nieprzenoszącym semantyki `availability_id` i zapisuje `UNAVAILABLE_24H` przez istniejący `durable_inputs.append_availability(...)`.

2. **Edycja istniejącego okresu** wskazuje konkretny `availability_id` i dopisuje nową wersję do tej samej rodziny. Zwykła korekta dat nie tworzy równoległej rodziny i nie mutuje historii.

3. Ekran pokazuje **wszystkie bieżące końce rodzin `UNAVAILABLE_24H`** tego pracownika (po jednym current chain end na `availability_id`) z ich zakresami dat. Nie pokazuje jako osobnych okresów superseded wersji tej samej rodziny; te pozostają historią.

4. Checkbox „Ogólna dostępność” nie jest osobnym persisted bool i nie identyfikuje jednej rodziny. Jest stanem wyliczanym z okresów:

   `general_available_on(d) = not any(r.active and r.kind == UNAVAILABLE_24H and r.start_date <= d <= r.end_date)`

   Czyli dla konkretnego dnia `d`: `✓` tylko gdy żaden bieżący aktywny okres `UNAVAILABLE_24H` go nie obejmuje; `☐` gdy obejmuje go co najmniej jeden. Jeżeli UI pokazuje pojedynczą zbiorczą kontrolkę bez jednego dnia, lista okresów pozostaje źródłem prawdy o osi czasu — kontrolka nie może być interpretowana jako „jedyny zapisany zakres”.

5. Nakładające się okresy tego samego rodzaju są dozwolone. Dla eligibility ich efekt jest idempotentny: jeden lub kilka obejmujących dany dzień oznacza tę samą blokadę. Nie wprowadzać mechanizmu merge/dedup tylko dla UI.

6. `AvailabilityRecord.active` zachowuje istniejące znaczenie końca rodziny, a nie „dzisiaj obowiązuje”. Rekord z `active=True`, którego `end_date` minął, może pozostać bieżącym końcem rodziny i po tej dacie nie blokuje. **Nie dodawać automatycznego wygaszania `active=False`.** Naturalny powrót do ✓ wynika z zakresu dat.

7. „Zgłoś nieobecność” i matryca nie dostają nowego pola provenance. Jeśli istnieje `UNAVAILABLE_24H`, jest tym samym faktem niezależnie od miejsca UI, z którego go utworzono. Screen 2 ma więc pokazywać wszystkie takie okresy, a nie próbować zgadywać ich pochodzenie.

## DLACZEGO NIE JEDNA RODZINA

Zamrożona decyzja właściciela definiuje odznaczenie jako czasowy zakres `od–do`, po którym automatycznie wraca stan bazowy; nie definiuje jednej trwałej rodziny na pracownika. Istniejący `AvailabilityRecord` jest append-only **per `availability_id`**, a `get_current_availability_for_employee()` zwraca jeden current chain end dla każdej rodziny i nie ogranicza ich liczby.

Wprowadzenie pojedynczości wymagałoby nowego invariant, atomowej operacji wyboru rodziny oraz reguły naprawy już istniejących wielu rodzin. To byłby nowy mechanizm produktu stworzony dla wyglądu pojedynczego checkboxa, a nie reuse istniejącego modelu.

Dodatkowo T010-B już przyjął rozróżnienie „edycja tego samego zapisu = ta sama rodzina” versus „nowy niezależny okres = nowa rodzina”. Rozstrzygnięcie Ogólnej dostępności pozostaje zgodne z tym precedensem.

## CO POZOSTAJE BEZ ZMIAN

- precedencja różnych `AvailabilityKind` (np. SICK_LEAVE nad LEAVE_GRANTED) nie jest tu projektowana ani zmieniana;
- solver/validator nie dostają nowej semantyki;
- nie powstaje nowy model nieobecności, tabela, kolumna ani stan checkboxa;
- `durable_inputs.append_availability` i `availability_repository` pozostają istniejącymi ownerami zapisu/historii;
- `employee_availability_matrix()` pozostaje istniejącym read ownerem dla ekranu;
- T021b pozostaje zamknięty i niezależny.

## IMPLEMENTATION BOUNDARY

Nie jest potrzebny osobny backendowy task „singularity”. FastAPI nie może wykonywać lookupu typu „znajdź jedyny aktualny blok i zdecyduj create/update”, ponieważ takiej pojedynczości nie ma.

Dla Screen 2 kontrakt implementacyjny ma jedynie:

- odczytać z istniejącej projekcji wszystkie current `UNAVAILABLE_24H` okresy;
- przy tworzeniu nowego okresu użyć nowego `availability_id`;
- przy korekcie wskazać konkretny istniejący `availability_id`;
- renderować stan dostępności z dat, a nie z istnienia jednej wybranej rodziny.

To rozstrzygnięcie odblokowuje wyłącznie kontrolkę „Ogólna dostępność”. Nie otwiera ponownie pozostałych elementów T021/T021b.