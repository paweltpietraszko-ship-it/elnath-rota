# ODLOZONE.md — rzeczy zauważone, świadomie odłożone

Backlog rzeczy, które CC lub Codex zauważyli, ale które NIE trafiają do
BOARD.md ani do pamięci CC między sesjami — żeby nie odżywały same z siebie
w każdej rozmowie. Ten plik czyta się tylko wtedy, gdy Paweł sam chce
wrócić do tematu. Jeden wpis = jedna sprawa, krótko, z datą i minimalnym
kontekstem żeby dało się to podjąć bez odtwarzania całej rozmowy.

Format wpisu:

```
## [data] Tytuł

Krótki opis (2-4 zdania). Dlaczego odłożone. Gdzie szukać więcej kontekstu
(plik, task, commit), jeśli trzeba wrócić.
```

---

## 2026-09-09 Solver nie dokłada reszty grafiku wokół jednego zaakceptowanego wyjątku od HARD

Gdy koordynator świadomie akceptuje złamanie reguły HARD dla jednej osoby
(np. trzecia zmiana pod rząd, praca mimo urlopu pozostawionego na papierze),
jedyny dziś dostępny mechanizm (Ręczna korekta) nie używa solvera wcale —
trzeba by ręcznie wpisać przypisania dla całego pozostałego miesiąca, nie
tylko dla spornej zmiany. Realny mechanizm byłby: koordynator wskazuje
jeden wyjątek, PLAN dokłada resztę automatycznie (podobnie jak dziś działa
automatyczne emergency-24h dla REST-01, tylko sterowane przez koordynatora
per przypadek, nie z góry ustawione na roli pracownika).

Odłożone: to niewygodność, nie blokada — świadome naruszenie i tak da się
dziś zapisać, tylko wolniej. Osobna sprawa od realnej, węższej luki z
brakiem wersji grafiku przy pierwszym zablokowanym PLAN (ta poszła do
architekta jako `ROTA-T057-ROUTE-A-REGRESSION`, main@2f7c43c). Nie
podejmować bez konkretnego, powtarzającego się przypadku z życia.

---
