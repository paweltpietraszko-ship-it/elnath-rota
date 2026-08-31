# PYTANIA_DO_TESTERA.md — otwarta lista pytań do rozstrzygnięcia przez testera

Nie jest to brief ani kontrakt Tasku. To rejestr pytań, na które nie da się
odpowiedzieć z kodu ani z dokumentów OWNER-frozen — bo dotyczą realnego
sposobu pracy koordynatora, a nie logiki programu. Odpowiedź daje tester
(człowiek używający Roty w praktyce), nie model. Wpis zamyka się dopiero
gdy odpowiedź jest znana i, jeśli trzeba, przechodzi do właściwego briefu/
FROZEN jako decyzja produktowa.

Format wpisu: data, pytanie, kontekst (dlaczego nie da się tego ustalić
inaczej), status (OTWARTE / ODPOWIEDZIANE — z odesłaniem gdzie).

---

## 2026-08-31 — Jak ustalać "sprawiedliwy" podział godzin?

**Kontekst.** Solver ma dziś realny mechanizm miękkiej sprawiedliwości
(`rota/planning/fairness.py::add_target_equity_fairness`,
`add_equal_split_fairness`) — ale to SOFT preferencja w funkcji celu, nie
twardy warunek. Przy 5 osobach na obiekcie może się zdarzyć, że rozkład
wyjdzie skrajny (np. 4×160h, 1×24h), jeśli inne ograniczenia (absencje,
brak dostępnych ludzi, umowy część-etatowe) mocno przeważą.

Paweł wyjaśnił wprost (2026-08-31), dlaczego to nie jest sam w sobie błąd
programu: **koordynator w realnej pracy widząc, że komuś wychodzi mało
godzin, po prostu wysyła tę osobę na urlop** — to koryguje bilans poza
Rotą, ręcznie, i Rota tego sama nie robi (Rota nie wystawia urlopów).
Sprawiedliwość "na sztywno co do godziny" nie jest więc zawsze celem —
bywa, że rozwiązaniem jest urlop, nie równiejszy grafik.

**Dlaczego to pytanie do testera, nie do kodu.** Program nie ma i nie
będzie miał zdefiniowanego progu "różnica ponad X godzin/X% = źle" — bo to
zależy od praktyki kadrowej danego obiektu/koordynatora, nie od logiki
planowania. Żaden automatyczny test (w tym Symulator Wariant A/B) nie może
sam wymyślić takiego progu — to byłoby dokładnie to, czego zakazano:
przemycanie nowej logiki produktu przez test.

**Pytanie.** Skąd tester ma wiedzieć, czy dany rozkład godzin (np. 4×160h,
1×24h) jest akceptowalny, czy wymaga interwencji (urlop, korekta ręczna)?
Czy jest jakaś praktyczna granica, powyżej której koordynator na pewno
reaguje urlopem — czy to zawsze decyzja kontekstowa (np. znane z góry
absencje, umowa, sezon)?

**Jak to wpływa na testowanie automatyczne (Symulator).** Dopóki nie ma
odpowiedzi: Symulator (żaden wariant) nie ocenia sprawiedliwości jako
PASS/FAIL. Może co najwyżej zaraportować surowy fakt (obserwowany spread
godzin) — bez osądu — dokładnie jak dziś ustalone dla Wariantu B.

**Status:** OTWARTE.

---
