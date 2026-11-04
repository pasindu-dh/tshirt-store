import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminCustomers from "./AdminCustomers";
import {
  getAdminCustomers,
  setAdminCustomerActive,
} from "../../api/adminCustomers";

vi.mock("../../api/adminCustomers", () => ({
  getAdminCustomers: vi.fn(),
  setAdminCustomerActive: vi.fn(),
}));

const CUSTOMER = {
  id: 5,
  name: "Nimal Perera",
  email: "nimal@example.com",
  role: "customer",
  is_active: true,
  created_at: "2026-01-10T10:00:00Z",
  order_count: 3,
  delivered_orders: 2,
  cancelled_orders: 1,
  gross_spend: 7500,
  refunded_total: 1000,
  pending_refund_total: 500,
  net_spend: 6500,
  returns_count: 2,
  open_returns: 1,
  last_order_at: "2026-02-01T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminCustomers />
    </MemoryRouter>
  );
}

describe("AdminCustomers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminCustomers.mockResolvedValue({
      customers: [CUSTOMER],
      total: 1,
    });
  });

  it("lists customers with spend, orders, and returns", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Customers" })
    ).toBeInTheDocument();
    expect(screen.getByText("Nimal Perera")).toBeInTheDocument();
    expect(screen.getByText("nimal@example.com")).toBeInTheDocument();
    expect(screen.getByText("Customer #5")).toBeInTheDocument();
    expect(screen.getByText("LKR 6500")).toBeInTheDocument();
    expect(screen.getByText("LKR 7500")).toBeInTheDocument();
    expect(screen.getByText("1 customer found")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View" })
    ).toHaveAttribute("href", "/admin/customers/5");

    expect(getAdminCustomers).toHaveBeenCalledWith({
      page: 1,
      limit: 10,
      search: undefined,
    });
  });

  it("deactivates a customer account", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    setAdminCustomerActive.mockResolvedValue({
      ...CUSTOMER,
      is_active: false,
    });

    renderPage();
    await screen.findByText("Nimal Perera");

    fireEvent.click(
      screen.getByRole("button", { name: "Deactivate" })
    );

    await waitFor(() => {
      expect(setAdminCustomerActive).toHaveBeenCalledWith(
        5,
        false
      );
    });
    expect(
      await screen.findByText("Nimal Perera deactivated.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Activate" })
    ).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    getAdminCustomers.mockResolvedValue({
      customers: [],
      total: 0,
    });

    renderPage();

    expect(
      await screen.findByText("No customers found.")
    ).toBeInTheDocument();
    expect(screen.getByText("0 customers found")).toBeInTheDocument();
  });
});
