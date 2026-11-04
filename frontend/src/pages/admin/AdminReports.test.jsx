import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminReports from "./AdminReports";
import { getAdminFinancialReport } from "../../api/adminOrders";

vi.mock("../../api/adminOrders", () => ({
  getAdminFinancialReport: vi.fn(),
}));

const REPORT = {
  date_from: null,
  date_to: null,
  group_by: "month",
  summary: {
    gross_revenue: 5000,
    refunded_total: 1000,
    pending_refund_total: 500,
    net_revenue: 4000,
    delivered_orders: 2,
    refund_count: 2,
    refunded_count: 1,
    returns_total: 3,
    open_returns: 1,
    completed_returns: 1,
    returned_units: 2,
  },
  periods: [
    {
      period: "2026-01",
      delivered_orders: 2,
      gross_revenue: 5000,
      refunded_total: 1000,
      net_revenue: 4000,
    },
  ],
  refund_statuses: [
    { status: "pending", count: 1, amount: 500 },
    { status: "processing", count: 0, amount: 0 },
    { status: "refunded", count: 1, amount: 1000 },
    { status: "failed", count: 0, amount: 0 },
  ],
  return_statuses: [
    { status: "requested", count: 1 },
    { status: "approved", count: 0 },
    { status: "rejected", count: 0 },
    { status: "completed", count: 1 },
    { status: "cancelled", count: 1 },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminReports />
    </MemoryRouter>
  );
}

describe("AdminReports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminFinancialReport.mockResolvedValue(REPORT);
  });

  it("shows financial totals, periods, and refund/return breakdowns", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Financial reports",
      })
    ).toBeInTheDocument();

    expect(screen.getByText("Gross revenue")).toBeInTheDocument();
    expect(screen.getAllByText("LKR 4000").length).toBeGreaterThan(0);
    expect(screen.getByText("LKR 500")).toBeInTheDocument();
    expect(screen.getByText("2026-01")).toBeInTheDocument();
    expect(screen.getByText("2 delivered orders")).toBeInTheDocument();
    expect(screen.getByText("requested")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View returns" })
    ).toHaveAttribute("href", "/admin/returns");

    expect(getAdminFinancialReport).toHaveBeenCalledWith({
      date_from: undefined,
      date_to: undefined,
      group_by: "month",
    });
  });

  it("applies date filters and daily grouping", async () => {
    renderPage();
    await screen.findByText("2026-01");

    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "2026-01-01" },
    });
    fireEvent.change(screen.getByLabelText("To"), {
      target: { value: "2026-01-31" },
    });
    fireEvent.change(screen.getByLabelText("Group by"), {
      target: { value: "day" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Apply" })
    );

    await waitFor(() => {
      expect(
        getAdminFinancialReport
      ).toHaveBeenLastCalledWith({
        date_from: "2026-01-01",
        date_to: "2026-01-31",
        group_by: "day",
      });
    });
  });

  it("rejects an inverted date range before fetching", async () => {
    renderPage();
    await screen.findByText("2026-01");
    getAdminFinancialReport.mockClear();

    fireEvent.change(screen.getByLabelText("From"), {
      target: { value: "2026-02-01" },
    });
    fireEvent.change(screen.getByLabelText("To"), {
      target: { value: "2026-01-01" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Apply" })
    );

    expect(
      screen.getByText(
        "The start date must be on or before the end date."
      )
    ).toBeInTheDocument();
    expect(getAdminFinancialReport).not.toHaveBeenCalled();
  });
});
