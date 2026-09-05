# ROTA-T056 — REAL PDF GATE A/B, ocena optyczna

Brief section 13, **T56-14 (GATE A)** i **T56-15 (GATE B)** — poprzednia
wersja tego pliku błędnie numerowała je jako T56-13/T56-14; poprawione po
uwadze Codexa (R13). Oba PDF wygenerowane przez rzeczywiste
`generate_schedule_pdf()` na realnych danych demonstracyjnych (prawdziwy
`:memory:` SQLite, prawdziwa persystencja `MonthlyExtraWorkCodes`,
prawdziwe `Assignment`/`ShiftDemand`) — nie mock, nie ręcznie sklejony
PDF. Oba pliki odczytane i obejrzane strona po stronie (renderowany
podgląd, nie tylko wyekstrahowany tekst).

## GATE A — `real_pdf_gate_a.pdf` (T56-14)

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
  kod miesiąca".
- **Brak kolizji/ucięcia**: legenda mieści się w całości pod siatką na tej
  samej stronie, tekst nie nachodzi na stopkę ("Strona 1 z 1" czytelna,
  oddzielona odstępem).
- **Skala szarości**: standardowe wypełnienie komórek D/N czytelne, spójne
  z istniejącym schematem sprzed T056.

Werdykt: PASS. (Codex R13 potwierdził niezależnie — Gate A nie wymagał poprawki.)

## GATE B — `real_pdf_gate_b.pdf` (T56-15)

**Poprawione po R13**: poprzednia wersja tego artefaktu (40 pracowników)
zmieściła legendę na ostatniej stronie siatki zamiast wymusić dedykowaną
stronę — nie ćwiczyła faktycznie ścieżki `legend_needs_own_page`/R8-04,
mimo że PDF wyglądał poprawnie. Nowy artefakt: **60 pracowników**, każdy z
własnym, unikalnym dodatkowym kodem D-rodziny (`D6`...`D65`), dobrane tak,
żeby ostatnia strona siatki była pełna (12 wierszy, brak miejsca na
legendę obok niej) — potwierdzone programowo przed renderem
(`_legend_required_height` > dostępne miejsce na stronie siatki).

Dokument wyszedł na **6 stronach**: 5 stron siatki grafiku (12 wierszy na
stronę, ostatnia pełna) + **1 osobna, dedykowana strona wyłącznie na
legendę** (strona 6), z jawnym nagłówkiem **"Legenda — ciąg dalszy
(wszystkie użyte oznaczenia)"** — dokładnie ścieżka `_draw_legend_only_page`
z R8-04.

Sprawdzone:
- **Strona 6 nie zawiera żadnego wiersza siatki** — wyłącznie nagłówek
  "ciąg dalszy" i pełna legenda; ostatni wiersz siatki (Pracownik EMP-9)
  jest na stronie 5, oddzielnie.
- **Kompletność**: wszystkie 60 użytych kodów wypisane (sprawdzone
  konkretnie `D6`, `D9`, `D65` — skrajne wartości — wszystkie obecne z
  poprawną liczbą godzin).
- **Czytelność**: dwie kolumny, rozmiar czcionki jak na stronie grafiku
  (nie zmniejszony), żaden wiersz nie zachodzi na kolejny.
- **Brak kolizji ze stopką**: legenda kończy się wyraźnie przed "Strona 6
  z 6".
- **Strony siatki (1-5)**: PLAN/WYK poprawne dla wszystkich 60
  pracowników, sumy godzin zgodne z przydzielonymi kodami, brak 0h.

Werdykt: PASS.

## Ograniczenia tej oceny

Wykonana przez CC (Claude Code) poprzez odczyt renderowanego podglądu obu
PDF, nie przez Pawła osobiście. Zgodnie z dotychczasową praktyką pipeline'u
(Codex sam wykonuje "ocenę optyczną" realnych PDF jako część audytu,
`tests_r10.txt`/`tests_r12.txt`/`tests_r13.txt`) — to jest przebieg tej
oceny po poprawce R13, podlega dalszemu, niezależnemu re-checkowi Codexa.
