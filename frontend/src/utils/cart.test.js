import { describe, expect, it } from "vitest";
import { getCartKey, normalizeCartItem } from "./cart";

describe("cart utilities", () => {
  it("builds a stable key for a product and variant", () => {
    expect(getCartKey(12, 34)).toBe("12:34");
    expect(getCartKey(12)).toBe("12:default");
  });

  it("normalizes legacy product items and preserves an existing key", () => {
    const normalized = normalizeCartItem({
      id: 7,
      name: "Legacy Tee",
      productId: 7,
    });

    expect(normalized.productId).toBe(7);
    expect(normalized.variantId).toBeNull();
    expect(normalized.key).toBe("7:default");

    const withKey = normalizeCartItem({
      productId: 8,
      variantId: 9,
      key: "custom-key",
    });

    expect(withKey.key).toBe("custom-key");
  });
});
