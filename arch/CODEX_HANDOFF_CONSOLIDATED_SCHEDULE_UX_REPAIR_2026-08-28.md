# HANDOFF DLA ARCHITEKTA — JEDNA NAPRAWA CODZIENNEJ PRACY Z GRAFIKIEM

**Źródło decyzji:** OWNER_CORRECTED, Paweł, 2026-08-28  
**Status:** do jednego briefu architektonicznego i jednego Tasku  
**Zakaz:** nie dzielić na trzy Taski i nie budować nowych subsystemów

## Cel właściciela

Naprawić za jednym razem trzy braki ujawnione podczas rzeczywistej pracy z
tym samym grafikiem miesiąca:

1. brak widocznego ostrzeżenia i skrajnie nierówny podział godzin, gdy jeden
   LOCAL nie ma `target_hours` dla planowanego miesiąca;
2. wejście „Ręczna korekta”, w którym koordynator nie może faktycznie wykonać
   korekty;
3. „Wydruk Grafiku”, który pozwala wyłącznie wygenerować/pobrać PDF, bez
   podglądu dokumentu przed pobraniem.

To jest jeden Task domykający codzienny przepływ grafiku, nie trzy nowe
capability.

## A. Brak targetu: ostrzeżenie i uczciwość

### OWNER_CONFIRMED

- program nie zgaduje i nie zapisuje targetu za koordynatora;
- brak targetu nie blokuje PLAN;
- wynik może zostać pokazany i użyty;
- mimo braku targetu solver ma domyślnie dzielić istniejącą pracę uczciwie
  między eligible LOCAL;
- koordynator ma zobaczyć po polsku, którego pracownika i miesiąca dotyczy
  brak danych oraz jaki ma on wpływ na bilans grafiku.

### Dowód istniejącego problemu

Live Test1, wrzesień 2026: pięciu LOCAL, cztery targety 176 h, jeden brakujący.
Wynik każdego z trzech kandydatów: 168/168/168/168/48. Brakujący pracownik
jest eligible, lecz assembler usuwa go z `state.work_balances`, a solver
buduje TARGET-01 i target equity tylko z tego zbioru.

Repo zawiera deklarowaną ścieżkę banneru
`assembler -> open_month -> MonthViewOut -> MonthlyPlanning`, ale właściciel
potwierdził, że na działającym ekranie ostrzeżenia nie widać. Architekt ma
wymagać pionowego reproduktora i wskazać faktyczne przerwanie tej ścieżki;
nie wolno uznać JSX za dowód naprawy.

### Granica

Architekt ma wskazać najmniejszy target-independent sygnał uczciwości
obejmujący każdego eligible LOCAL. Nie wolno syntetyzować `target_hours`,
dodawać drugiego WorkBalance ani rozbudowywać analytics.

## B. Ręczna korekta ma rzeczywiście umożliwiać korektę

### OWNER_CONFIRMED

Po wejściu przez pozycję „Ręczna korekta” koordynator ma od razu rozumieć,
jak wybrać pozycję grafiku, i móc użyć już istniejących operacji:

- przypisz istniejącą zmianę innej osobie;
- zamroź/odmroź;
- oznacz zaplanowaną PRIMARY jako NN.

Nie powstaje osobny silnik korekt. Backend i router tych operacji już istnieją.

### Potwierdzony problem source-shape

- pozycja nawigacji ładuje ten sam `MonthlyPlanning`, bez wejścia w jawny
  tryb korekty ani instrukcji;
- korekta pojawia się dopiero po kliknięciu małego tekstu D/N w komórce;
- dla wersji FINAL `onSelectAssignment` jest wyłączone, mimo że backend
  korekty tworzy nową wersję potomną;
- T037 świadomie nie wystawił dodawania przypisania do pustej komórki.

### Granica

Naprawić dostępność i czytelność trzech istniejących operacji. Nie dodawać
edycji pustych komórek, nowego formularza Assignment ani odłożonego dry-run
manual correction bez osobnej decyzji właściciela.

## C. Podgląd istniejącego PDF

### OWNER_CONFIRMED

Po wygenerowaniu PDF koordynator ma zobaczyć jego podgląd w aplikacji i móc
go następnie pobrać. Sam automatyczny download nie wystarcza.

### Potwierdzony problem source-shape

Backend już zwraca `pdf_base64`. `Export.tsx` natychmiast tworzy Blob,
uruchamia download i usuwa URL; nie zachowuje dokumentu do podglądu.

### Granica

Użyć tego samego wyniku `generate_schedule_pdf`. Nie tworzyć drugiego
generatora, osobnego modelu wydruku ani drugiego endpointu, jeśli istniejący
payload wystarcza. Architekt ma rozstrzygnąć wyłącznie minimalny lifecycle
Blob URL: podgląd, pobranie, zastąpienie i zwolnienie zasobu.

## Wymagany kształt jednego Tasku

Task powinien mieć trzy pionowe scenariusze akceptacyjne, ale jeden wspólny
zakres i jeden branch:

1. brak targetu na realnym pięcioosobowym obiekcie: widoczne ostrzeżenie,
   pracownik nie znika z target-independent fairness, grafik pozostaje
   możliwy do pokazania i użycia;
2. wejście „Ręczna korekta”: wybór istniejącej zmiany i każda z trzech
   istniejących operacji przechodzi UI -> API -> application -> nowa wersja
   -> readback;
3. wydruk: jeden backendowy PDF jest najpierw widoczny w podglądzie, a potem
   pobierany bez ponownego generatora.

Testy mają dowodzić tych trzech szwów. Nie powtarzać pełnych kontraktów
solvera, manual_edit ani schedule_export, które mają własnych właścicieli.

## Poza zakresem

- nowe ekrany nawigacyjne;
- drugi system ostrzeżeń;
- nowy generator PDF lub drugi model wydruku;
- nowy backend ręcznej korekty;
- edycja pustych komórek;
- refaktor solvera, assemblera, całego `MonthlyPlanning` albo T021;
- analytics, historia, decyzje koordynatora i pozostałe findings PR #9.
