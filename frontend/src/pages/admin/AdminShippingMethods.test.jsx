import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminShippingMethods from "./AdminShippingMethods";
import {
  createAdminShippingMethod,
  deleteAdminShippingMethod,
  getAdminShippingMethods,
  updateAdminShippingMethod,
} from "../../api/adminShipping";

vi.mock("../../api/adminShipping", () => ({
  getAdminShippingMethods: vi.fn(),
  createAdminShippingMethod: vi.fn(),
  updateAdminShippingMethod: vi.fn(),
  deleteAdminShippingMethod: vi.fn(),
}));

const METHOD = {
  id: 1,
  name: "Standard Delivery",
  description: "Within Sri Lanka.",
  fee_lkr: 350,
  is_active: true,
  sort_order: 0,
  created_at: "2026-11-04T10:00:00Z",
  updated_at: "2026-11-04T10:00:00Z",
};

function renderPage() {
  return render(<AdminShippingMethods />);
}

describe("AdminShippingMethods", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminShippingMethods.mockResolvedValue([METHOD]);
    createAdminShippingMethod.mockResolvedValue(METHOD);
    updateAdminShippingMethod.mockResolvedValue({
      ...METHOD,
      is_active: false,
    });
    deleteAdminShippingMethod.mockResolvedValue();
  });

  it("lists shipping methods", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Shipping methods",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Standard Delivery")
    ).toBeInTheDocument();
    expect(screen.getByText("LKR 350")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Add method" })
    ).toBeInTheDocument();
  });

  it("creates a shipping method", async () => {
    renderPage();
    await screen.findByText("Standard Delivery");

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Express Delivery" },
    });
    fireEvent.change(screen.getByLabelText("Fee (LKR)"), {
      target: { value: "900" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Add method" })
    );

    await waitFor(() => {
      expect(createAdminShippingMethod).toHaveBeenCalledWith({
        name: "Express Delivery",
        description: "",
        fee_lkr: 900,
        is_active: true,
        sort_order: 0,
      });
    });
    expect(
      await screen.findByText("Shipping method created.")
    ).toBeInTheDocument();
  });

  it("deactivates and deletes a method", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();
    await screen.findByText("Standard Delivery");

    fireEvent.click(
      screen.getByRole("button", { name: "Deactivate" })
    );

    await waitFor(() => {
      expect(updateAdminShippingMethod).toHaveBeenCalledWith(
        1,
        { is_active: false }
      );
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Delete" })
    );

    await waitFor(() => {
      expect(deleteAdminShippingMethod).toHaveBeenCalledWith(1);
    });
  });
});
