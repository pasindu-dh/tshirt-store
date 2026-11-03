import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import ProductCard from "./ProductCard";

vi.mock("../hooks/useAuth", () => ({
  default: () => ({ user: null }),
}));

vi.mock("../hooks/useWishlist", () => ({
  default: () => ({
    isWishlisted: () => false,
    toggleWishlist: vi.fn(),
  }),
}));

function renderCard(product) {
  return render(
    <MemoryRouter>
      <ProductCard product={product} />
    </MemoryRouter>
  );
}

describe("ProductCard", () => {
  it("shows the product details and links to its detail page", () => {
    renderCard({
      id: 1,
      name: "Aurora Tee",
      slug: "aurora-tee",
      price: 2500,
      image: "/images/aurora.jpg",
      category: { name: "T-Shirts" },
      variants: [{ stock: 3 }],
    });

    expect(screen.getByRole("heading", { name: "Aurora Tee" })).toBeInTheDocument();
    expect(screen.getByText("LKR 2500")).toBeInTheDocument();
    expect(screen.getByText("T-Shirts")).toBeInTheDocument();
    expect(screen.queryByText("Out of stock")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Add Aurora Tee to wishlist",
      })
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /Aurora Tee|View product/ })[0]
    ).toHaveAttribute("href", "/product/aurora-tee");
  });

  it("marks a product as out of stock when every variant is empty", () => {
    renderCard({
      id: 2,
      name: "Sold Out Tee",
      slug: "sold-out-tee",
      price: 1800,
      image: "/images/sold-out.jpg",
      category: null,
      variants: [{ stock: 0 }, { stock: 0 }],
    });

    expect(screen.getByText("Out of stock")).toBeInTheDocument();
  });
});
