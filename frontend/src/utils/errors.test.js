import { describe, expect, it } from "vitest";
import { getApiError } from "./errors";

describe("getApiError", () => {
  it("returns a string detail from the API", () => {
    expect(
      getApiError({ response: { data: { detail: "Cart is empty" } } })
    ).toBe("Cart is empty");
  });

  it("joins validation messages", () => {
    expect(
      getApiError({
        response: {
          data: {
            detail: [
              { msg: "Email is invalid" },
              { msg: "Password is too short" },
            ],
          },
        },
      })
    ).toBe("Email is invalid Password is too short");
  });

  it("uses the fallback for unknown errors", () => {
    expect(getApiError(new Error("network"))).toBe(
      "Something went wrong. Please try again."
    );
    expect(getApiError(null, "Custom fallback")).toBe("Custom fallback");
  });
});
