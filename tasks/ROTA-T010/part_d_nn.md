# ROTA-T010-D — NN

STATUS: DRAFT FOR CODEX AUDIT

NN dotyczy jednej konkretnej zmiany już istniejącej w grafiku.

Wymagania:
- wcześniejsza wersja grafiku zachowuje stan planowany;
- nowa wersja powstaje przez istniejącą ręczną korektę;
- w nowej wersji niewykonana zmiana nie liczy godzin pracy i ma trwały kod `NN`;
- nie zapisujemy wykonanej pracy, jeśli jej nie było;
- nie tworzymy z NN reguły dostępności pracownika;
- korekta nie uruchamia automatycznie ponownego układania grafiku;
- ewentualne faktyczne zastępstwo zapisuje istniejący mechanizm ręcznej korekty.

Testy muszą potwierdzić zachowanie historii, 0 godzin z NN oraz brak wpływu NN na reguły dostępności.

Pełna semantyka produktu wynika z Aneksu właścicielskiego.