import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import OrderEditForm from "./OrderEditForm";

const ORDER = {
  id: 12,
  contact_name: "Nimal Perera",
  contact_email: "nimal@example.com",
  phone: "0771234567",
  address_line1: "12 Main Street",
  address_line2: "",
  city: "Colombo",
  postal_code: "00100",
  country: "Sri Lanka",
  notes: "Leave at the gate.",
};

describe("OrderEditForm", () => {
  it("submits the edited customer and shipping fields", () => {
    const onSave = vi.fn();

    render(
      <OrderEditForm
        order={ORDER}
        onSave={onSave}
        onCancel={vi.fn()}
        saving={false}
        error=""
      />
    );

    fireEvent.change(screen.getByLabelText("Contact name"), {
      target: { value: "Nimal P. Perera" },
    });
    fireEvent.change(screen.getByLabelText("City"), {
      target: { value: "Kandy" },
    });
    fireEvent.change(screen.getByLabelText("Internal notes"), {
      target: { value: "Call before delivery." },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Save details" })
    );

    expect(onSave).toHaveBeenCalledWith({
      contact_name: "Nimal P. Perera",
      contact_email: "nimal@example.com",
      phone: "0771234567",
      address_line1: "12 Main Street",
      address_line2: "",
      city: "Kandy",
      postal_code: "00100",
      country: "Sri Lanka",
      notes: "Call before delivery.",
    });
  });

  it("shows an API error and supports cancelling", () => {
    const onCancel = vi.fn();

    render(
      <OrderEditForm
        order={ORDER}
        onSave={vi.fn()}
        onCancel={onCancel}
        saving={false}
        error="Order is already shipped."
      />
    );

    expect(
      screen.getByText("Order is already shipped.")
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Cancel" })
    );
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
