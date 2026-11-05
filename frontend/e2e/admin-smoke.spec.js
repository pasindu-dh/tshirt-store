import { expect, test } from "@playwright/test";
import {
  API_URL,
  BASE_URL,
  adminCredentials,
} from "./env.js";

const disposableDatabase =
  process.env.E2E_DISPOSABLE_DB === "1" || process.env.CI === "true";

test.skip(
  !disposableDatabase,
  "Point the backend at a disposable database and set E2E_DISPOSABLE_DB=1."
);

test.skip(
  !adminCredentials.email || !adminCredentials.password,
  "Set E2E_ADMIN_EMAIL/E2E_ADMIN_PASSWORD or configure backend/.env."
);

test("admin pages and readiness checks load", async ({
  page,
  request,
}) => {
  const ready = await request.get(`${API_URL}/health/ready`);
  expect(ready.status()).toBe(200);
  expect((await ready.json()).status).toBe("ready");

  await page.goto(`${BASE_URL}/login`);
  await page.getByLabel("Email").fill(adminCredentials.email);
  await page.getByLabel("Password").fill(adminCredentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/admin");

  const pages = [
    ["/admin", "Dashboard"],
    ["/admin/orders", "Orders"],
    ["/admin/customers", "Customers"],
    ["/admin/notifications", "Notifications"],
    ["/admin/returns", "Returns"],
    ["/admin/refunds", "Refunds"],
    ["/admin/reviews", "Reviews"],
    ["/admin/reports", "Financial reports"],
    ["/admin/reports/products", "Product performance"],
    ["/admin/inventory", "Inventory"],
    ["/admin/products/import", "Import product catalog"],
    ["/admin/shipping-methods", "Shipping methods"],
  ];

  for (const [path, heading] of pages) {
    await page.goto(`${BASE_URL}${path}`);
    await expect(
      page.getByRole("heading", { name: heading, exact: true })
    ).toBeVisible();
  }
});
