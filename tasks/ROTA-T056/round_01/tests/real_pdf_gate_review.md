# ROTA-T056 — REAL PDF GATE A/B, ocena optyczna

Brief section 13, T56-13/T56-14. Oba PDF wygenerowane przez rzeczywiste
`generate_schedule_pdf()` na realnych danych demonstracyjnych (prawdziwy
`:memory:` SQLite, prawdziwa persystencja `MonthlyExtraWorkCodes`,
prawdziwe `Assignment`/`ShiftDemand`) — nie mock, nie ręcznie sklejony
PDF. Oba pliki odczytane i obejrzane strona po stronie (renderowany
podgląd, nie tylko wyekstrahowany tekst).

## GATE A — `real_pdf_gate_a.pdf` (T56-13)

Scenariusz: 3 pracowników, 3 dodatkowe kody D/N tego samego miesiąca —
`D6` (rodzina D, suffix=6), `N6` (rodzina N, suffix=6, `end_next_day`),
`D9` (suffix > 6, sprawdza że mechanizm nie jest zaszyty pod "tylko 6").
Wszystkie użyte kody mieszczą się czytelnie na stronie grafiku (1 strona
łącznie).

Sprawdzone:
- **PLAN/WYK**: `D6`, `N6`, `D9` poprawnie w obu wierszach (PLAN i WYK)
  dla właściwego pracownika i daty; `N6` poprawnie zacieniowany na obu
  dniach, które obejmuje (`end_next_day`).
- **Sumy**: `Plan g.`/`Wyk. g.` = 14 / 10 / 17 — dokładnie zgodne z
  długością zdefiniowanych intervali (14h, 10h, 17h), nigdy 0.
- **Znaczenie wszystkich użytych oznaczeń**: legenda wypisuje dokładnie
  `D6 = 14h`, `N6 = 10h`, `D9 = 17h`, wszystkie oznaczone jako "dodatkowy
  kod miesiąca" — żaden nieużyty standardowy kod (D1-D5/N1-N5 poza D/N
  rzeczywiście użytymi) nie zaśmieca legendy.
- **Brak kolizji/ucięcia**: legenda mieści się w całości pod siatką na tej
  samej stronie, tekst nie nachodzi na stopkę ("Strona 1 z 1" czytelna,
  oddzielona odstępem).
- **Skala szarości**: standardowe wypełnienie komórek D/N (jasnoszare/
  ciemnoszare) czytelne, spójne z istniejącym schematem sprzed T056 — nie
  zmienione przez ten task.

Werdykt: PASS.

## GATE B — `real_pdf_gate_b.pdf` (T56-14)

Scenariusz: 40 pracowników, każdy z własnym, unikalnym dodatkowym kodem
D-rodziny (`D6`...`D45`) o innej długości i innych godzinach zegarowych —
wystarczająco dużo faktycznie użytych oznaczeń, żeby legenda nie mieściła
się już na stronie grafiku. Dokument wyszedł na 4 stronach: 3 strony
siatki grafiku + **1 dedykowana strona wyłącznie na legendę** (strona 4).

Sprawdzone:
- **Kompletność drugiej (tu: czwartej) strony**: wszystkie 40 użytych
  kodów wypisane, żaden nie brakuje (zweryfikowane też programowo —
  `_used_codes(model)` zwróciło 40 pozycji, tyle samo widać na wydruku).
- **Czytelność**: dwie kolumny, stały rozmiar czcionki jak na stronie
  grafiku (nie zmniejszony), żaden wiersz nie zachodzi na kolejny.
- **Brak utraty oznaczeń**: konkretnie sprawdzone `D6`, `D9`, `D45` (skrajne
  wartości) — wszystkie obecne z poprawną liczbą godzin.
- **Brak kolizji ze stopką**: legenda kończy się wyraźnie przed "Strona 4
  z 4", zgodnie z naprawą R8-04 (sprawdzenie `available_on_own_page`
  przed umieszczeniem na dedykowanej stronie zamiast zakładać, że się
  zmieści).
- **Strony siatki (1-3)**: PLAN/WYK poprawne dla wszystkich 40
  pracowników, sumy godzin zgodne z przydzielonymi kodami, brak 0h.

Werdykt: PASS.

## Ograniczenia tej oceny

Wykonana przez CC (Claude Code) poprzez odczyt renderowanego podglądu obu
PDF, nie przez Pawła osobiście. Zgodnie z dotychczasową praktyką pipeline'u
(Codex sam wykonuje "ocenę optyczną" realnych PDF jako część audytu,
`tests_r10.txt`/`tests_r12.txt`) — to jest pierwszy przebieg tej oceny,
podlega dalszemu, niezależnemu re-checkowi Codexa/architekta.
