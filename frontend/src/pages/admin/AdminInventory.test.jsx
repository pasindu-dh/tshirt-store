import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminInventory from "./AdminInventory";
import {
  adjustStock,
  getLowStock,
  getStockMovements,
} from "../../api/adminInventory";

vi.mock("../../api/adminInventory", () => ({
  adjustStock: vi.fn(),
  getLowStock: vi.fn(),
  getStockMovements: vi.fn(),
}));

const LOW_STOCK = {
  variants: [
    {
      id: 1,
      product_id: 10,
      product_name: "Aurora Tee",
      product_slug: "aurora-tee",
      image: "/images/aurora.jpg",
      size: "M",
      color: "Black",
      sku: "AUR-M",
      stock: 2,
      low_stock_threshold: 5,
    },
  ],
  total: 1,
};

const MOVEMENTS = {
  movements: [
    {
      id: 7,
      variant_id: 1,
      product_id: 10,
      order_id: 44,
      return_request_id: null,
      actor_user_id: 1,
      movement_type: "order_placed",
      quantity_delta: -2,
      stock_before: 4,
      stock_after: 2,
      product_name: "Aurora Tee",
      size: "M",
      color: "Black",
      sku: "AUR-M",
      reason: "Order #44 placed.",
      created_at: "2026-11-04T10:00:00Z",
    },
  ],
  total: 1,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminInventory />
    </MemoryRouter>
  );
}

describe("AdminInventory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getLowStock.mockResolvedValue(LOW_STOCK);
    getStockMovements.mockResolvedValue(MOVEMENTS);
  });

  it("shows low-stock variants and movement history", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Inventory" })
    ).toBeInTheDocument();
    expect(screen.getAllByText("Aurora Tee").length).toBeGreaterThan(
      0
    );
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(
      screen.getByRole("cell", { name: "Order placed" })
    ).toBeInTheDocument();
    expect(screen.getByText("-2")).toBeInTheDocument();
    expect(screen.getByText("4 → 2")).toBeInTheDocument();
    expect(screen.getByText("Admin #1")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Order #44" })
    ).toHaveAttribute("href", "/admin/orders/44");

    expect(getLowStock).toHaveBeenCalledWith({
      search: undefined,
      limit: 100,
    });
    expect(getStockMovements).toHaveBeenCalledWith({
      page: 1,
      limit: 20,
      movement_type: undefined,
      search: undefined,
      date_from: undefined,
      date_to: undefined,
    });
  });

  it("submits a manual stock adjustment", async () => {
    adjustStock.mockResolvedValue({
      variant: {
        ...LOW_STOCK.variants[0],
        stock: 5,
      },
      movement: {
        ...MOVEMENTS.movements[0],
        movement_type: "manual_adjustment",
        quantity_delta: 3,
        stock_before: 2,
        stock_after: 5,
      },
    });

    renderPage();
    await screen.findAllByText("Aurora Tee");

    fireEvent.click(
      screen.getByRole("button", { name: "Adjust" })
    );
    fireEvent.change(
      screen.getByLabelText("Stock adjustment quantity"),
      { target: { value: "3" } }
    );
    fireEvent.change(
      screen.getByLabelText("Stock adjustment reason"),
      { target: { value: "Restock delivery." } }
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Save adjustment" })
    );

    await waitFor(() => {
      expect(adjustStock).toHaveBeenCalledWith(1, {
        quantity_delta: 3,
        reason: "Restock delivery.",
      });
    });

    expect(
      await screen.findByText(
        "Stock updated for Aurora Tee (M/Black): 2 → 5."
      )
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(getLowStock.mock.calls.length).toBeGreaterThan(1);
    });
  });

  it("rejects a zero adjustment before calling the API", async () => {
    renderPage();
    await screen.findAllByText("Aurora Tee");

    fireEvent.click(
      screen.getByRole("button", { name: "Adjust" })
    );
    fireEvent.change(
      screen.getByLabelText("Stock adjustment quantity"),
      { target: { value: "0" } }
    );
    fireEvent.change(
      screen.getByLabelText("Stock adjustment reason"),
      { target: { value: "No change." } }
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Save adjustment" })
    );

    expect(
      screen.getByText(
        "Enter a non-zero whole-number stock change."
      )
    ).toBeInTheDocument();
    expect(adjustStock).not.toHaveBeenCalled();
  });
});
