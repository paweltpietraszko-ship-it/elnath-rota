function nextDayIso(dayIso) {
  const [y, m, d] = dayIso.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + 1));
  return `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, "0")}-${String(next.getUTCDate()).padStart(2, "0")}`;
}
const old = (d) => new Date(new Date(`${d}T00:00:00`).getTime() + 86400000).toISOString().slice(0, 10);
for (const d of ["2026-10-16","2026-10-24","2026-10-25","2026-03-28","2026-03-29","2026-10-31","2026-12-31","2028-02-28","2028-02-29"]) console.log(process.env.TZ, d, "old", old(d), "new", nextDayIso(d));
