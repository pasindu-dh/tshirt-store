import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Navbar from "./Navbar";

vi.mock("../hooks/useAuth", () => ({
  default: () => ({
    user: null,
    isAdmin: false,
    logout: vi.fn(),
  }),
}));

vi.mock("../hooks/useCart", () => ({
  default: () => ({
    cartCount: 0,
    openCart: vi.fn(),
  }),
}));

function renderNavbar() {
  return render(
    <MemoryRouter>
      <Navbar search="" setSearch={vi.fn()} />
    </MemoryRouter>
  );
}

describe("Navbar mobile menu", () => {
  it("opens and closes the mobile navigation panel", () => {
    renderNavbar();

    fireEvent.click(
      screen.getByRole("button", { name: "Open menu" })
    );

    expect(
      screen.getByRole("button", { name: "Create account" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Close menu" })
    ).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(
      screen.getByRole("button", { name: "Close menu" })
    );

    expect(
      screen.queryByRole("button", { name: "Create account" })
    ).not.toBeInTheDocument();
  });
});
