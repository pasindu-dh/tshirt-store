import { describe, expect, it } from "vitest";
import { buildDailySeries, dateRangeDays } from "./sales";

describe("sales chart helpers", () => {
  it("builds an inclusive UTC date range", () => {
    const range = dateRangeDays(
      7,
      new Date("2026-11-04T12:00:00Z")
    );

    expect(range).toEqual({
      dateFrom: "2026-10-29",
      dateTo: "2026-11-04",
    });
  });

  it("fills missing periods with zero values", () => {
    const series = buildDailySeries(
      [
        {
          period: "2026-11-01",
          net_revenue: 1000,
          delivered_orders: 1,
        },
      ],
      "2026-10-31",
      "2026-11-02",
      "net_revenue"
    );

    expect(series).toEqual([
      { period: "2026-10-31", value: 0 },
      { period: "2026-11-01", value: 1000 },
      { period: "2026-11-02", value: 0 },
    ]);
  });

  it("supports other numeric period fields", () => {
    const series = buildDailySeries(
      [
        {
          period: "2026-11-01",
          delivered_orders: 3,
        },
      ],
      "2026-11-01",
      "2026-11-01",
      "delivered_orders"
    );

    expect(series).toEqual([
      { period: "2026-11-01", value: 3 },
    ]);
  });

  it("returns an empty series for invalid ranges", () => {
    expect(
      buildDailySeries(
        [],
        "2026-11-05",
        "2026-11-01",
        "net_revenue"
      )
    ).toEqual([]);
    expect(
      buildDailySeries([], null, null, "net_revenue")
    ).toEqual([]);
  });
});
