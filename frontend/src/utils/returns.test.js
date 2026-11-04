import { describe, expect, it } from "vitest";
import {
  RETURN_REASON_LABELS,
  getReturnDeadline,
  isReturnWindowOpen,
} from "./returns";

describe("return policy helpers", () => {
  it("calculates the deadline from delivery time", () => {
    const deadline = getReturnDeadline(
      "2026-01-01T00:00:00Z",
      30
    );

    expect(deadline.toISOString()).toBe(
      "2026-01-31T00:00:00.000Z"
    );
  });

  it("treats a zero window as no deadline", () => {
    expect(
      getReturnDeadline("2026-01-01T00:00:00Z", 0)
    ).toBeNull();
    expect(
      getReturnDeadline("2026-01-01T00:00:00Z", 30)
    ).not.toBeNull();
  });

  it("checks whether the window is still open", () => {
    expect(
      isReturnWindowOpen(
        "2026-01-01T00:00:00Z",
        30,
        new Date("2026-01-30T23:59:59Z")
      )
    ).toBe(true);
    expect(
      isReturnWindowOpen(
        "2026-01-01T00:00:00Z",
        30,
        new Date("2026-01-31T00:00:01Z")
      )
    ).toBe(false);
    expect(
      isReturnWindowOpen(
        "2026-01-01T00:00:00Z",
        0,
        new Date("2027-01-01T00:00:00Z")
      )
    ).toBe(true);
  });

  it("maps structured reason codes to labels", () => {
    expect(RETURN_REASON_LABELS.size_fit).toBe("Size or fit");
    expect(RETURN_REASON_LABELS.damaged).toBe(
      "Item arrived damaged"
    );
    expect(RETURN_REASON_LABELS.other).toBe("Other");
  });
});
