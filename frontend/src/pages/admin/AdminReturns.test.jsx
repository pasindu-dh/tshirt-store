import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminReturns from "./AdminReturns";
import { getAdminReturns } from "../../api/adminOrders";

vi.mock("../../api/adminOrders", () => ({
  getAdminReturns: vi.fn(),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminReturns />
    </MemoryRouter>
  );
}

describe("AdminReturns", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists return requests with order links and refund state", async () => {
    getAdminReturns.mockResolvedValue({
      returns: [
        {
          id: 4,
          order_id: 12,
          status: "requested",
          reason: "Wrong size.",
          created_at: "2026-11-04T10:00:00Z",
          order_contact_name: "Nimal Perera",
          order_contact_email: "nimal@example.com",
          order_total: 5000,
          item_count: 2,
          refund_id: null,
          refund_status: null,
        },
      ],
      total: 1,
    });

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Returns" })
    ).toBeInTheDocument();
    expect(screen.getByText("#4")).toBeInTheDocument();
    expect(screen.getByText("Wrong size.")).toBeInTheDocument();
    expect(screen.getByText("Nimal Perera")).toBeInTheDocument();
    expect(screen.getByText("2 items")).toBeInTheDocument();
    expect(screen.getByText("requested")).toBeInTheDocument();
    expect(screen.getByText("1 return request found")).toBeInTheDocument();

    const orderLinks = screen.getAllByRole("link", {
      name: "Order #12",
    });
    expect(orderLinks[0]).toHaveAttribute(
      "href",
      "/admin/orders/12"
    );
    expect(
      screen.getByRole("link", { name: "Review" })
    ).toHaveAttribute("href", "/admin/orders/12");
  });

  it("shows an empty state when there are no returns", async () => {
    getAdminReturns.mockResolvedValue({ returns: [], total: 0 });

    renderPage();

    expect(
      await screen.findByText("No return requests found.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("0 return requests found")
    ).toBeInTheDocument();
  });
});
