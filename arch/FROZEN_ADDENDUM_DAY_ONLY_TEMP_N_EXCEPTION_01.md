# DAY-ONLY-TEMP-N-EXCEPTION-01

STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM

Koordynator może czasowo dopuścić N pracownikowi z `Employee.day_only=true`. To jest jeden wąski wyjątek od `DAY_ONLY-01`, nie ogólny override HARD.

Nowy rodzaj `SiteRuleVersion`: `EMPLOYEE_DAY_ONLY_N_EXCEPTION` z parametrem `employee_id`. Musi być `CONFIRMED_EXCEPTION`, `HARD`, `RESOLVED` i korzysta z istniejących `effective_from/effective_to`.

Gdy reguła jest obowiązująca dla tego pracownika/Site i demand jest N, wyłącznie `DAY_ONLY-01` uznaje się za spełnione. Dla D reguła nic nie zmienia.

Reguła NIE uchyla membership, aktywności Employee, Availability, REST, LOAD, coverage ani żadnego innego HARD SiteRule. Wszystkie pozostałe HARD nadal łączą się przez AND.

Po `effective_to` `DAY_ONLY-01` ponownie działa bez operacji przywracającej. Eligibility i validator muszą mieć identyczne zachowanie.

Testy: dzień przed, obie granice, środek i dzień po zakresie; równoczesny inny zakaz N; choroba/urlop; disabled membership; zgodność eligibility/validator.

Zakaz: żadnego ogólnego mechanizmu `override` / `exception wins`.