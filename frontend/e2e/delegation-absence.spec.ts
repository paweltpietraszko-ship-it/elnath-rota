// ROTA-DELEGACJA-ABSENCE-KIND brief.md section 15 (Frontend/API minimal
// tests): the Site delegation-default-hours resource (section 4) is
// genuinely self-contained -- no role catalog or roster setup needed,
// unlike the full "add employee -> zgłoś delegację" flow this file does
// not attempt to cover end to end (see BOARD.md handoff note: written but
// not executed against a live dev server in this session).
import { test, expect } from "@playwright/test";
import { createSite, openSite } from "./helpers";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

test("DEL: Site delegation default hours can be set and reloads correctly", async ({ page }) => {
  const displayName = `DEL-${uid()}`;
  await createSite(page, displayName);
  await openSite(page, displayName);

  // Panel sterowania lands on the "Obiekt" tab by default.
  await page.getByRole("heading", { name: "Domyślne godziny delegacji" }).waitFor();
  const input = page.locator("text=Domyślne godziny delegacji").locator("..").locator('input[type="number"]');
  await input.fill("7");
  await page.getByRole("button", { name: "Zapisz" }).last().click();
  await page.getByText("Zapisano.").waitFor();

  await page.reload();
  await page.getByRole("heading", { name: "Domyślne godziny delegacji" }).waitFor();
  await expect(input).toHaveValue("7");
});
