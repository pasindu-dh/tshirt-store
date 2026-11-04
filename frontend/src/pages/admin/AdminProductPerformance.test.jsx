import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminProductPerformance from "./AdminProductPerformance";
import { getAdminProductReport } from "../../api/adminOrders";

vi.mock("../../api/adminOrders", () => ({
  getAdminProductReport: vi.fn(),
}));

const REPORT = {
  date_from: null,
  date_to: null,
  summary: {
    units_sold: 10,
    gross_revenue: 25000,
    returned_units: 1,
    return_rate: 10.0,
    products_sold: 2,
    current_stock_value: 50000,
    low_stock_variants: 3,
    out_of_stock_variants: 1,
  },
  products: [
    {
      product_id: 1,
      product_name: "Alpha Tee",
      product_slug: "alpha-tee",
      category_id: 2,
      category_name: "T-Shirts",
      units_sold: 8,
      order_count: 5,
      gross_revenue: 20000,
      returned_units: 1,
      return_rate: 12.5,
      current_stock: 12,
      stock_value: 30000,
      low_stock_variants: 1,
    },
    {
      product_id: null,
      product_name: "Deleted Tee",
      product_slug: "deleted-tee",
      category_id: null,
      category_name: "Uncategorized",
      units_sold: 2,
      order_count: 2,
      gross_revenue: 5000,
      returned_units: 0,
      return_rate: 0.0,
      current_stock: 0,
      stock_value: 0,
      low_stock_variants: 0,
    },
  ],
  categories: [
    {
      category_id: 2,
      category_name: "T-Shirts",
      product_count: 1,
      units_sold: 8,
      gross_revenue: 20000,
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminProductPerformance />
    </MemoryRouter>
  );
}

describe("AdminProductPerformance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminProductReport.mockResolvedValue(REPORT);
  });

  it("shows product and category performance", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Product performance",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("Units sold")).toBeInTheDocument();
    expect(screen.getAllByText("LKR 25000").length).toBeGreaterThan(0);
    expect(screen.getAllByText("10%").length).toBeGreaterThan(0);
    expect(screen.getByText("Alpha Tee")).toBeInTheDocument();
    expect(screen.getByText("Deleted Tee")).toBeInTheDocument();
    expect(screen.getByText("Deleted")).toBeInTheDocument();
    expect(screen.getByText("T-Shirts")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Edit" })
    ).toHaveAttribute("href", "/admin/products/1/edit");

    expect(getAdminProductReport).toHaveBeenCalledWith({
      date_from: undefined,
      date_to: undefined,
      limit: 20,
    });
  });

  it("applies date filters and top-product limit", async () => {
    renderPage();
    await screen.findByText("Alpha Tee");

    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "2026-03-01" },
    });
    fireEvent.change(screen.getByLabelText("To"), {
      target: { value: "2026-03-31" },
    });
    fireEvent.change(screen.getByLabelText("Top products"), {
      target: { value: "10" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Apply" })
    );

    await waitFor(() => {
      expect(getAdminProductReport).toHaveBeenLastCalledWith({
        date_from: "2026-03-01",
        date_to: "2026-03-31",
        limit: 10,
      });
    });
  });
});
