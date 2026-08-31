# REQUEST — co dalej z evaluatorem grafików po ROTA-T044

Status: **DYSKUSJA — prośba o opinię Codexa i architekta, nie brief, nie kontrakt**

Data: 2026-08-31
Kontekst: ROTA-T044 (Symulator Koordynatora Wariant B) zmergowany do `main`
(`30d2489`), architekt PASS na `ARCHITECT_IMPLEMENTATION_REVIEW_R2.md`.

## 1. Problem, wprost od OWNERA

> "mamy grafiki, które nikt/nic nie analizuje."

Wariant B (i wcześniej Wariant A) generuje realne, zróżnicowane grafiki
przez prawdziwy backend/solver i — świadomie, zgodnie z kontraktem T044 —
**nigdy nie ocenia ich jakości**. To był celowy wybór (Symulator ma badać
mechanizm, nie być drugim sędzią — patrz `tasks/ROTA-T044/brief.md`
sekcja 1). Ale to zostawia realną, nazwaną przez OWNERA lukę: nikt nie
patrzy na te grafiki po fakcie. Człowiek nie ogarnie ręcznie setek
przebiegów; nic automatycznego tego dziś nie robi.

## 2. Co już jest ustalone (nie do ponownego negocjowania w tej dyskusji)

Z rozmowy OWNERA i CC po T044, zapisane w pamięci projektowej CC:

- Evaluator to **osobny, downstream proces**, konsumujący surowy JSON,
  który Symulator już zapisuje — nie coś wplecione w sam Symulator. Próba
  wbudowania oceny W Symulator była już raz odrzucona (T043 Checkpoint B:
  `evaluate_fairness`/`compute_quarter_oracle`) jako dokładnie ten błąd,
  którego unikamy.
- Evaluator **nie ma duplikować obliczeń, które już mają zielone testy**
  (legalność przez prawdziwy `validate()`, bilans przez `rota/balance.py`)
  — ma je CZYTAĆ z już zapisanych faktów (Wariant B od `ARCH-R1-01`
  zapisuje `readback.analytics`/`readback.month_view` w każdym raporcie),
  nie liczyć od nowa.
- Realna "matematyka" evaluatora (jeśli w ogóle jakaś powstanie) dotyczy
  wyłącznie tego, czego produkt DZIŚ nie liczy wcale (np. fairness/spread
  godzin) — a to jest ŚWIADOME rozszerzenie zakresu, nie odtwarzanie
  istniejącej logiki.
- OWNER-owy pomysł: **mały skrypt + jedno wywołanie LLM** do oceny
  jakościowej ("czy ten grafik wygląda sensownie jako całość"), zamiast
  próby zakodowania wyczerpującej listy reguł. LLM nie ma liczyć
  arytmetyki na dużych danych (do tego jest zawodny) — tylko oceniać
  jakościowo to, czego nie da się łatwo sprowadzić do reguły.
- Kolejność: evaluator budowany DOPIERO po tym, jak sam Symulator ma PASS
  niezależnego audytu — inaczej evaluator ocenia dane zniekształcone przez
  błędy generatora, nie pracę solvera (to się już raz potwierdziło: R10-01
  do R13-02 to realne błędy Symulatora znalezione PO pierwszym PASS
  Codexa na samym kontrakcie). T044 ma teraz PASS architekta na
  implementacji, więc ten warunek jest spełniony.

## 3. Co się zmieniło od czasu tamtej rozmowy (nowy fakt techniczny)

Podczas implementacji T044 (`ARCH-R1-01`, `R13-01`) powstał realny,
przetestowany mechanizm: `_write_completed_report()` zapisuje pełny,
surowy snapshot (obiekt, kalkulator, absencje, kolejność akcji, PLAN/
EXTERNAL/REPLAN, `readback.analytics`/`readback.month_view`, gotowa
komenda reprodukcji) dla **każdego** zakończonego przykładu Hypothesis —
nie tylko awarii. To jest dokładnie ten "format, który przyszły evaluator
mógłby skonsumować", o którym mówi brief.md sekcja 1.6.

**Ale jest tu otwarte pytanie architektoniczne, którego jeszcze nikt nie
rozstrzygnął:** te pliki JSON świadomie NIE są commitowane do repo
(traktowane jako efemeryczne dane z przebiegu testu, nie trwałe
znalezisko jak `failures/**`) — żyją tylko lokalnie, na dysku, dopóki
ktoś ich nie usunie. Jeśli evaluator ma być osobnym, PÓŹNIEJSZYM procesem
(inna sesja, inny czas), potrzebuje albo:

- (a) uruchamiać się w tej samej sesji/na tym samym dysku zaraz po
  przebiegu Symulatora, zanim ktoś posprząta katalog `reports/`, albo
- (b) mieć jakiś trwalszy sposób przekazania tych danych (np. faktyczne
  zapisanie ich do repo/artefaktu, przesłanie gdzieś, inny mechanizm) —
  co jest już realną zmianą kontraktu, nie tylko "czytaniem tego co jest".

To pytanie nie było jeszcze nikomu zadane wprost.

## 4. Pytania do Codexa i architekta

1. **Kiedy i jak evaluator ma dostawać dane?** Czy to ma być mały skrypt
   uruchamiany ręcznie zaraz po przebiegu Symulatora (czytający lokalny,
   świeży `reports/`), czy potrzebujemy trwalszej ścieżki (evaluator jako
   osobny Task, ale wymagający zmiany "nie commitujemy raportów" na "
   commitujemy/eksportujemy raporty gdzieś")?
2. **Jaki zakres wejścia:** tylko nowe raporty Wariantu B, czy też
   istniejące `failures/**` Wariantu A (inny format, inny zestaw pól)?
3. **Jaka forma wyjścia evaluatora:** wolna notatka tekstowa per obiekt
   (najbliższe pierwotnemu pomysłowi OWNERA — "czy wygląda sensownie"),
   czy jakaś ustandaryzowana etykieta/kategoria? Kto to potem czyta —
   OWNER bezpośrednio, czy trafia to do kolejnego automatycznego kroku?
4. **Czy jest tu realne ryzyko "overengineering spiral"** (już raz
   zdarzone w tym projekcie, patrz historia elnath-code) — evaluator
   wymyślający hipotetyczne problemy zamiast raportować to, co faktycznie
   widzi w danych? Jak się przed tym zabezpieczyć w samym brifie, zanim
   ktokolwiek zacznie pisać kod?
5. Czy to w ogóle powinien być pełny Task z takim samym ciężkim procesem
   jak T044 (brief → audyt → Task → adwokat diabła → implementacja →
   audyty), czy — skoro to głównie "skrypt + jeden prompt do LLM", a nie
   złożona logika testowa — zasługuje na lżejszy proces?

## 5. Czego ta dyskusja NIE rozstrzyga

- Nie jest to jeszcze brief ani kontrakt — to zebranie pytań przed
  napisaniem czegokolwiek.
- Nie zmienia niczego w T044 (zmergowane, zamknięte).
- Nie zakłada z góry żadnej odpowiedzi na pytania w sekcji 4 — to
  świadomie otwarte pytania do Codexa/architekta, nie retoryczne.
