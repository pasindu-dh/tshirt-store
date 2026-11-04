import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import SalesOverview from "./SalesOverview";

const REPORT = {
  date_from: "2026-11-01",
  date_to: "2026-11-03",
  summary: {
    net_revenue: 5000,
    delivered_orders: 3,
    refunded_total: 500,
    open_returns: 1,
  },
  periods: [
    {
      period: "2026-11-01",
      net_revenue: 1000,
      delivered_orders: 1,
    },
    {
      period: "2026-11-02",
      net_revenue: 2000,
      delivered_orders: 2,
    },
    {
      period: "2026-11-03",
      net_revenue: 2000,
      delivered_orders: 0,
    },
  ],
};

const PRODUCTS = {
  products: [
    {
      product_id: 1,
      product_name: "Alpha Tee",
      product_slug: "alpha-tee",
      gross_revenue: 3000,
      units_sold: 2,
    },
    {
      product_id: 2,
      product_name: "Beta Tee",
      product_slug: "beta-tee",
      gross_revenue: 2000,
      units_sold: 1,
    },
  ],
};

function renderOverview(overrides = {}) {
  const onRangeChange = vi.fn();

  render(
    <MemoryRouter>
      <SalesOverview
        report={REPORT}
        products={PRODUCTS}
        rangeDays={30}
        onRangeChange={onRangeChange}
        loading={false}
        error=""
        {...overrides}
      />
    </MemoryRouter>
  );

  return { onRangeChange };
}

describe("SalesOverview", () => {
  it("renders revenue, order, and top-product charts", () => {
    renderOverview();

    expect(
      screen.getByRole("heading", { name: "Sales overview" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Net revenue chart" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Delivered orders chart",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("Alpha Tee")).toBeInTheDocument();
    expect(screen.getByText("Beta Tee")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Full report →" })
    ).toHaveAttribute("href", "/admin/reports/products");
  });

  it("changes the reporting period", () => {
    const { onRangeChange } = renderOverview();

    fireEvent.change(
      screen.getByLabelText("Sales overview period"),
      { target: { value: "7" } }
    );

    expect(onRangeChange).toHaveBeenCalledWith(7);
  });

  it("shows empty sales states", () => {
    renderOverview({
      report: {
        ...REPORT,
        summary: {
          net_revenue: 0,
          delivered_orders: 0,
          refunded_total: 0,
          open_returns: 0,
        },
        periods: [],
      },
      products: { products: [] },
    });

    expect(
      screen.getByText(
        "No delivered revenue in this period."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("No product sales in this period.")
    ).toBeInTheDocument();
  });
});
