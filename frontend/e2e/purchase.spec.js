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

test("a shopper can complete the full purchase journey", async ({
  page,
  request,
}) => {
  const stamp = Date.now().toString(36);
  const productName = `E2E Tee ${stamp}`;
  const sku = `E2E-${stamp}-M`;
  const customerEmail = `e2e-${stamp}@furzy.dev`;
  const customerPassword = "E2ECustomerPass123!";
  const couponCode = `E2E-${stamp}`.toUpperCase();
  let productId = null;
  let couponId = null;
  let orderId = null;

  try {
    const adminLogin = await request.post(`${API_URL}/auth/login`, {
      form: {
        username: adminCredentials.email,
        password: adminCredentials.password,
      },
    });
    expect(adminLogin.status()).toBe(200);
    const adminToken = (await adminLogin.json()).access_token;
    const adminHeaders = {
      Authorization: `Bearer ${adminToken}`,
    };

    const productResponse = await request.post(
      `${API_URL}/admin/products`,
      {
        headers: adminHeaders,
        data: {
          name: productName,
          description: "Created by the end-to-end purchase test.",
          price: 2450,
          images: ["/images/t_shirt_01.jpg"],
          variants: [
            {
              size: "M",
              color: "Black",
              sku,
              stock: 5,
            },
          ],
        },
      }
    );
    expect(productResponse.status()).toBe(201);
    const product = await productResponse.json();
    productId = product.id;

    const couponResponse = await request.post(
      `${API_URL}/admin/coupons`,
      {
        headers: adminHeaders,
        data: {
          code: couponCode,
          description: "Playwright checkout discount",
          discount_type: "percent",
          value: 10,
          min_subtotal: 0,
          usage_limit: 5,
          is_active: true,
        },
      }
    );
    expect(couponResponse.status()).toBe(201);
    couponId = (await couponResponse.json()).id;

    const customerResponse = await request.post(
      `${API_URL}/auth/register`,
      {
        data: {
          name: "E2E Customer",
          email: customerEmail,
          password: customerPassword,
        },
      }
    );
    expect(customerResponse.status()).toBe(201);

    await page.goto(`${BASE_URL}/product/${product.slug}`);
    await expect(
      page.getByRole("heading", { name: productName })
    ).toBeVisible();

    await page.getByRole("button", { name: "Add to cart" }).click();
    await expect(page.getByText("Added to cart.")).toBeVisible();

    await page.getByRole("button", { name: "Checkout" }).click();
    await page.waitForURL("**/login");

    await page.getByLabel("Email").fill(customerEmail);
    await page.getByLabel("Password").fill(customerPassword);
    await page.getByRole("button", { name: "Sign in" }).click();

    await page.waitForURL("**/checkout");
    await expect(
      page.getByRole("heading", { name: "Checkout" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Place order" })
    ).toBeVisible();

    await page.getByLabel("Phone").fill("0771234567");
    await page.getByLabel("Address line 1").fill("123 E2E Street");
    await page.getByLabel("City").fill("Colombo");
    await page
      .getByLabel("Order notes (optional)")
      .fill("Playwright purchase journey");

    await page.getByLabel("Coupon code").fill(couponCode);
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(
      page.getByText(new RegExp(`${couponCode} applied`))
    ).toBeVisible();
    await expect(page.getByText("- LKR 245")).toBeVisible();

    await page.getByRole("button", { name: "Place order" }).click();
    await page.waitForURL(/\/orders\/\d+$/);
    orderId = Number(page.url().match(/\/orders\/(\d+)$/)[1]);
    await expect(
      page.getByText("Order placed successfully")
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Order #\d+/ })
    ).toBeVisible();
    await expect(page.getByText(productName).first()).toBeVisible();
    await expect(page.getByText(`Discount (${couponCode})`)).toBeVisible();

    await page.goto(`${BASE_URL}/product/${product.slug}`);
    await page
      .getByLabel("Title (optional)")
      .fill("End-to-end review");
    await page
      .getByLabel("Review (optional)")
      .fill("Submitted by the Playwright purchase journey.");
    await page.getByRole("button", { name: "Submit review" }).click();
    await expect(
      page.getByText("Thanks for reviewing this product.")
    ).toBeVisible();

    await page
      .getByRole("button", {
        name: "Add this product to your wishlist",
      })
      .click();
    await expect(
      page.getByRole("button", {
        name: "Remove this product from your wishlist",
      })
    ).toBeVisible();

    await page.goto(`${BASE_URL}/wishlist`);
    await expect(
      page.getByRole("heading", { name: "My wishlist" })
    ).toBeVisible();
    await expect(page.getByText(productName).first()).toBeVisible();
    await page
      .getByRole("button", {
        name: `Remove ${productName} from wishlist`,
      })
      .click();
    await expect(
      page.getByText(/Your wishlist is empty/)
    ).toBeVisible();

    // Break the access token without touching the refresh token, then use
    // in-app navigation so the axios refresh interceptor must recover.
    await page.goto(`${BASE_URL}/orders/${orderId}`);
    await expect(
      page.getByRole("heading", { name: `Order #${orderId}` })
    ).toBeVisible();

    await page.evaluate(() => {
      const raw = localStorage.getItem("furzy-auth");
      const auth = JSON.parse(raw);
      auth.access_token = "expired-for-e2e";
      localStorage.setItem("furzy-auth", JSON.stringify(auth));
    });

    await page.getByRole("link", { name: "Back to orders" }).click();
    await page.waitForURL("**/orders");
    await expect(
      page.getByRole("heading", { name: "My orders" })
    ).toBeVisible();
    await expect(page.getByText(productName).first()).toBeVisible();
  } finally {
    if (productId !== null || couponId !== null) {
      const login = await request.post(`${API_URL}/auth/login`, {
        form: {
          username: adminCredentials.email,
          password: adminCredentials.password,
        },
      });

      if (login.ok()) {
        const token = (await login.json()).access_token;
        const headers = { Authorization: `Bearer ${token}` };

        if (couponId !== null) {
          await request.delete(
            `${API_URL}/admin/coupons/${couponId}`,
            { headers }
          );
        }

        if (productId !== null) {
          await request.delete(
            `${API_URL}/admin/products/${productId}`,
            { headers }
          );
        }
      }
    }
  }
});
