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

  it("explains when the API cannot be reached", () => {
    expect(
      getApiError(
        { request: {}, code: "ERR_NETWORK" },
        "Unable to sign in."
      )
    ).toBe(
      "Cannot reach the server. Check that the backend is running and try again."
    );
  });

  it("explains a request timeout", () => {
    expect(
      getApiError({ request: {}, code: "ECONNABORTED" })
    ).toBe(
      "The server took too long to respond. Please try again."
    );
  });

  it("uses the fallback for unknown errors", () => {
    expect(getApiError(new Error("network"))).toBe(
      "Something went wrong. Please try again."
    );
    expect(getApiError(null, "Custom fallback")).toBe("Custom fallback");
  });
});
