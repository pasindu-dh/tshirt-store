import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminCustomerDetail from "./AdminCustomerDetail";
import { getAdminCustomer } from "../../api/adminCustomers";

vi.mock("../../api/adminCustomers", () => ({
  getAdminCustomer: vi.fn(),
}));

const CUSTOMER = {
  id: 5,
  name: "Nimal Perera",
  email: "nimal@example.com",
  role: "customer",
  created_at: "2026-01-10T10:00:00Z",
  order_count: 1,
  delivered_orders: 1,
  cancelled_orders: 0,
  gross_spend: 2850,
  refunded_total: 500,
  pending_refund_total: 0,
  net_spend: 2350,
  returns_count: 1,
  open_returns: 0,
  last_order_at: "2026-02-01T10:00:00Z",
  orders: [
    {
      id: 101,
      status: "delivered",
      payment_method: "cod",
      payment_status: "paid",
      total: 2850,
      created_at: "2026-02-01T10:00:00Z",
      items: [
        {
          id: 1,
          product_name: "Aurora Tee",
          quantity: 2,
        },
      ],
    },
  ],
  returns: [
    {
      id: 7,
      order_id: 101,
      status: "completed",
      reason: "Wrong size.",
      created_at: "2026-02-02T10:00:00Z",
      items: [
        {
          id: 3,
          product_name: "Aurora Tee",
          color: "Black",
          size: "M",
          quantity: 1,
          restocked_at: "2026-02-03T10:00:00Z",
        },
      ],
      refund: {
        id: 9,
        amount: 500,
        status: "refunded",
      },
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/admin/customers/5"]}>
      <Routes>
        <Route
          path="/admin/customers/:customerId"
          element={<AdminCustomerDetail />}
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("AdminCustomerDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminCustomer.mockResolvedValue(CUSTOMER);
  });

  it("shows customer lifetime totals, orders, and returns", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Nimal Perera",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/nimal@example.com · Customer #5/)
    ).toBeInTheDocument();
    expect(screen.getByText("LKR 2350")).toBeInTheDocument();
    expect(
      screen.getAllByText("LKR 2850").length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Order #101").length
    ).toBeGreaterThan(0);
    expect(screen.getByText(/Return #7/)).toBeInTheDocument();
    expect(screen.getByText("Wrong size.")).toBeInTheDocument();
    expect(screen.getByText(/Refund LKR 500/)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Order #101" })
    ).toHaveAttribute("href", "/admin/orders/101");
    expect(getAdminCustomer).toHaveBeenCalledWith("5");
  });
});
