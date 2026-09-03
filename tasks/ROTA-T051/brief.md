# ROTA-T051 — skrócenie i spolszczenie technicznych hashy na wydruku i ekranie Wydruku

STATUS: PROPOZYCJA DO WERYFIKACJI CC — ZERO KODU PRODUKTU — IMPLEMENTACJA
DOPIERO PO PASS PREIMPLEMENTATION AUDIT

BASE_MAIN_SHA: `965b2b8bc90f7d6aeae49222235d3f31b0fc9d66`

Źródło: znalezisko zgłoszone przez Paweł podczas omawiania T048 — wydruk
PDF (i ekran „Wydruk") pokazują koordynatorowi surowe, 64-znakowe hashe
techniczne. OWNER: skrócić hasza, nie usuwać całkiem, ewentualnie nadać
ludzki opis.

## 1. Cel

Trzy miejsca pokazują dziś pełny, 64-znakowy hash sha256 wprost
koordynatorowi, plus jedno z nich ma dodatkowo angielską etykietę.
Skrócić widoczny hash do krótkiego, wciąż użytecznego do porównania
fragmentu (10 pierwszych znaków — ten sam rząd wielkości co skrócony hash
gita, wystarczający do stwierdzenia "czy to ten sam wydruk"), spolszczyć
etykiety. Rzeczywista, pełna wartość hasha (`document_revision`
zwracany przez API, użyty do realnych porównań w kodzie/testach) zostaje
bez zmian — skracane jest wyłącznie to, co się rysuje/wyświetla.

## 2. Trzy miejsca

- `rota/application/schedule_export.py::_provenance_text` (linia 124-128):
  zwraca `f"Schedule provenance: {lineage[-1].version_id} /
  lineage-sha256:{digest}"` — angielska etykieta ORAZ pełny 64-znakowy
  `digest`. Wartość tej funkcji trafia na wydruk (`model.provenance_text`,
  rysowane w `_draw_page_header`, linia 591) — nigdzie indziej (sprawdzone:
  `schedule_provenance` w odpowiedzi API jest zadeklarowane w
  `frontend/src/api/client.ts:331`, ale nigdy nie jest renderowane w
  żadnym ekranie).
- `rota/application/schedule_export.py::_draw_page_header` (linia 592):
  rysuje `f"Revision: {revision}   Wygenerowano: ..."` — angielska
  etykieta i pełny 64-znakowy `revision` (= `_document_revision(model)`,
  obliczony raz w `_render_pdf` linia 603, przekazany jako parametr).
- `frontend/src/screens/Export.tsx:89`: `` `Gotowe. Wersja dokumentu:
  ${res.document_revision}.` `` — już po polsku, ale pokazuje pełny
  64-znakowy hash wprost w komunikacie sukcesu na ekranie „Wydruk".

## 3. Co świadomie NIE jest zmieniane

- `_document_revision(model)` (schedule_export.py:436-452) i
  `_provenance_text`'s wewnętrzny `digest` — same funkcje liczące hash
  zostają bez zmian. `document_revision`/`schedule_provenance` w
  odpowiedzi API (`api/routers/export.py:86-87`, zwracane w pełnej
  długości) też zostają bez zmian — to są realne identyfikatory
  techniczne, których długość/format mogą sprawdzać inne narzędzia.
  Skracane jest wyłącznie to, co się **rysuje na PDF** i **wyświetla w
  komunikacie** na ekranie, w miejscu rysowania/wyświetlania, nie u
  źródła.
- `lineage[-1].version_id` w `_provenance_text` (np. `SV-<uuid>`) — bez
  zmian. OWNER prosił o skrócenie hasza, nie o usunięcie identyfikatora
  wersji z wydruku; to osobna sprawa, nietknięta w tym Tasku.
- Test `tests/test_t020.py:167,169` sprawdza tylko równość/nierówność
  `_document_revision(m1)`/`_document_revision(m2)`/`_document_revision(m3)`
  — wywołuje funkcję bezpośrednio, nie czyta wydruku ani ekranu, więc nie
  jest tym Taskiem naruszany (funkcja niezmieniona).

## 4. Wymagane zachowanie

`_provenance_text` (schedule_export.py:124-128) — zamienić zwracany
string na:

```python
return f"Wersja źródłowa: {lineage[-1].version_id} — kod weryfikacyjny {digest[:10]}"
```

`_draw_page_header` (schedule_export.py:592) — zamienić rysowaną linię na:

```python
c.drawString(MARGIN, y, f"Rewizja treści: {revision[:10]}   Wygenerowano: {generated_at.isoformat()}"); y -= 16  # noqa: E702
```

`frontend/src/screens/Export.tsx:89` — zamienić na:

```tsx
setResult({
  ok: true,
  message: `Gotowe. Wersja dokumentu: ${res.document_revision ? res.document_revision.slice(0, 10) : res.document_revision}.`,
});
```

(zachowuje dzisiejsze zachowanie dla `null` — `res.document_revision` jest
`string | null`; skracanie następuje tylko, gdy wartość faktycznie
istnieje).

## 5. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Minimalna konieczna zmiana |
|---|---|---|
| `_provenance_text` | dokładny przykład OWNERA | zmiana treści jednego zwracanego stringa |
| `_draw_page_header` revision | dokładny przykład OWNERA | zmiana treści jednej rysowanej linii |
| `Export.tsx` komunikat sukcesu | dokładny przykład OWNERA | jeden `.slice(0, 10)` w istniejącym template literalu |

Usunięte z propozycji jako zbędne: zmiana `_document_revision`/`_provenance_text`'s
sposobu liczenia hasha, zmiana pól odpowiedzi API, usunięcie
`lineage[-1].version_id` z wydruku, jakakolwiek zmiana logiki
`document_revision`/`schedule_provenance`.

## 6. TASK_SCOPE

Dozwolony kod produktu:

- `rota/application/schedule_export.py`
- `frontend/src/screens/Export.tsx`

Dozwolone testy i dokumenty:

- `tasks/ROTA-T051/brief.md`
- nowe testy jednostkowe wyłącznie dla zmienionego tekstu powyżej, jeśli
  sensowne (np. `_provenance_text`/`_draw_page_header`'s efekt na
  wyrenderowany tekst)

Poza zakresem: `api/routers/export.py`, `frontend/src/api/client.ts`,
`_document_revision`, jakakolwiek zmiana solvera/API/kontraktu odpowiedzi.

## 7. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `rota/application/schedule_export.py --symbol _provenance_text`
  - `rota/application/schedule_export.py --symbol _document_revision`
- REASON: Task zmienia prezentację wartości zwracanych przez istniejących
  właścicieli; trzeba potwierdzić, że skrócenie w miejscu rysowania nie
  dotyka żadnego innego callera, który mógłby oczekiwać pełnej długości.

Wykonane na `BASE_MAIN_SHA` (`where.py`): `_provenance_text` — jedna
definicja, jeden produkcyjny caller w tym samym pliku (linia 81),
wartość trafia wyłącznie do `model.provenance_text`, rysowanego w
`_draw_page_header`. `_document_revision` — jedna definicja, dwa
produkcyjni callerzy w tym samym pliku: linia 58 (pole odpowiedzi API,
**nietykane**, zostaje pełnej długości) i linia 603 (`revision` do
rysowania na PDF, **tu następuje skrócenie, tylko w miejscu rysowania**).
Testowe wywołania (`tests/test_t020.py:167,169`) sprawdzają tylko
równość/nierówność pełnej wartości zwracanej przez funkcję — nie są
naruszane, bo sama funkcja się nie zmienia.

## 8. Macierz odbioru

- **T51-01 — wydruk bez pełnego hasza:** wygenerowany PDF nie zawiera
  nigdzie 64-znakowego ciągu — ani w linii „Wersja źródłowa", ani w linii
  „Rewizja treści"; oba pokazują dokładnie 10 pierwszych znaków
  odpowiedniej wartości.
- **T51-02 — etykiety po polsku:** żadna z tych dwóch linii nie zawiera
  słów „Schedule provenance" ani „Revision".
- **T51-03 — identyfikator wersji bez zmian:** `lineage[-1].version_id`
  nadal pojawia się w linii „Wersja źródłowa" w pełnej, niezmienionej
  postaci.
- **T51-04 — ekran Wydruku skrócony:** po udanym eksporcie komunikat
  sukcesu pokazuje 10 pierwszych znaków `document_revision`, nie pełne 64.
- **T51-05 — `null` bez zmian:** jeśli `res.document_revision` jest
  `null`, komunikat wygląda dokładnie tak jak dziś (bez wyjątku, bez
  „undefined").
- **T51-06 — brak regresji hasza:** `_document_revision`/`_provenance_text`
  nadal zwracają pełną, niezmienioną wartość przy bezpośrednim wywołaniu;
  `tests/test_t020.py:167,169` nadal przechodzą bez zmian.

## 9. Weryfikacja proporcjonalna do zmiany

Implementator uruchamia:

- celowane T51-01…T51-06 (backend łatwo testowalny na `_provenance_text`/
  `_render_pdf` bezpośrednio; frontend przez najprostszy dostępny w repo
  mechanizm, inaczej ręczna weryfikacja z opisem w DELIVERY);
- `tests/test_t020.py` (cały plik, szybki, potwierdza brak regresji na
  `_document_revision`);
- `ruff check rota/application/schedule_export.py`;
- lintowanie/typecheck frontendu, jeśli repo ma taki krok skonfigurowany;
- `git diff --check`.

Pełna suita repozytorium jest opcjonalna i wymaga osobnej zgody OWNERA.

## 10. Proces i oczekiwany werdykt CC

Trzy niezależne, mechaniczne zmiany prezentacji istniejących wartości —
zero nowej logiki, zero zmiany kontraktu API. Architekt nie jest
potrzebny.

Oczekiwany werdykt preimplementation:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` tylko z konkretnym `TRACE`, `OWNERSHIP` i reproduktorem sprzeczności.

Do PASS: CC READ-ONLY.

## 11. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T051/brief.md
- rota/application/schedule_export.py
- frontend/src/screens/Export.tsx
