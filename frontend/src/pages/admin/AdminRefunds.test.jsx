import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminRefunds from "./AdminRefunds";
import { getAdminRefunds } from "../../api/adminRefunds";

vi.mock("../../api/adminRefunds", () => ({
  getAdminRefunds: vi.fn(),
}));

const REFUND = {
  id: 3,
  order_id: 44,
  payment_id: 7,
  amount: 500,
  kind: "return",
  status: "pending",
  provider: "manual",
  provider_refund_id: "",
  reason: "Wrong size.",
  notes: "",
  created_at: "2026-11-04T10:00:00Z",
  completed_at: null,
  order_contact_name: "Nimal Perera",
  order_contact_email: "nimal@example.com",
  order_total: 5000,
  order_status: "delivered",
  order_payment_status: "paid",
  payment_reference: "PAY-REFERENCE-1",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminRefunds />
    </MemoryRouter>
  );
}

describe("AdminRefunds", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminRefunds.mockResolvedValue({
      refunds: [REFUND],
      total: 1,
    });
  });

  it("lists global refunds with order and customer context", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Refunds" })
    ).toBeInTheDocument();
    expect(screen.getByText("#3")).toBeInTheDocument();
    expect(screen.getByText("Nimal Perera")).toBeInTheDocument();
    expect(screen.getByText("nimal@example.com")).toBeInTheDocument();
    expect(screen.getByText("LKR 500")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("return")).toBeInTheDocument();
    expect(
      screen.getByText("PAY-REFERENCE-1")
    ).toBeInTheDocument();
    expect(screen.getByText("1 refund record found")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Order #44" })[0]
    ).toHaveAttribute("href", "/admin/orders/44");
    expect(
      screen.getByRole("link", { name: "View order" })
    ).toHaveAttribute("href", "/admin/orders/44");

    expect(getAdminRefunds).toHaveBeenCalledWith({
      page: 1,
      limit: 10,
      search: undefined,
      status: undefined,
      kind: undefined,
      date_from: undefined,
      date_to: undefined,
    });
  });

  it("shows an empty state", async () => {
    getAdminRefunds.mockResolvedValue({
      refunds: [],
      total: 0,
    });

    renderPage();

    expect(
      await screen.findByText("No refunds found.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("0 refund records found")
    ).toBeInTheDocument();
  });
});
