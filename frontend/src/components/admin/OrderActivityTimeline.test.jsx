import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import OrderActivityTimeline from "./OrderActivityTimeline";

const EVENTS = [
  {
    id: "order-created",
    type: "order",
    title: "Order placed",
    description: "Test Customer placed an order for LKR 2450.",
    actor: "Test Customer",
    created_at: "2026-11-05T10:00:00Z",
  },
  {
    id: "audit-1",
    type: "status",
    title: "Order confirmed",
    description: "Status changed from pending to confirmed.",
    actor: "Test Admin",
    created_at: "2026-11-05T10:05:00Z",
  },
];

describe("OrderActivityTimeline", () => {
  it("renders the consolidated events in order", () => {
    render(<OrderActivityTimeline events={EVENTS} />);

    expect(
      screen.getByRole("heading", { name: "Activity timeline" })
    ).toBeInTheDocument();
    expect(screen.getByText("Order placed")).toBeInTheDocument();
    expect(screen.getByText("Order confirmed")).toBeInTheDocument();
    expect(screen.getByText("Test Customer")).toBeInTheDocument();
    expect(screen.getByText("Test Admin")).toBeInTheDocument();

    const titles = screen
      .getAllByText(/Order (placed|confirmed)/)
      .map((node) => node.textContent);
    expect(titles).toEqual(["Order placed", "Order confirmed"]);
  });

  it("shows loading, error, and empty states", () => {
    const { rerender } = render(
      <OrderActivityTimeline events={[]} loading />
    );
    expect(
      screen.getByText("Loading order activity...")
    ).toBeInTheDocument();

    rerender(
      <OrderActivityTimeline events={[]} error="Could not load." />
    );
    expect(screen.getByText("Could not load.")).toBeInTheDocument();

    rerender(<OrderActivityTimeline events={[]} />);
    expect(
      screen.getByText(
        "No activity has been recorded for this order."
      )
    ).toBeInTheDocument();
  });
});
