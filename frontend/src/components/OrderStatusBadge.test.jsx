import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import OrderStatusBadge from "./OrderStatusBadge";

describe("OrderStatusBadge", () => {
  it("renders a known status", () => {
    render(<OrderStatusBadge status="shipped" />);

    expect(screen.getByText("shipped")).toBeInTheDocument();
  });

  it("renders an unknown status without crashing", () => {
    render(<OrderStatusBadge status="processing" />);

    expect(screen.getByText("processing")).toBeInTheDocument();
  });
});
