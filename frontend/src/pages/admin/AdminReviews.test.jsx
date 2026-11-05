import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminReviews from "./AdminReviews";
import {
  deleteAdminReview,
  getAdminReviews,
  updateAdminReviewStatus,
} from "../../api/adminReviews";

vi.mock("../../api/adminReviews", () => ({
  getAdminReviews: vi.fn(),
  updateAdminReviewStatus: vi.fn(),
  deleteAdminReview: vi.fn(),
}));

const REVIEW = {
  id: 1,
  product_id: 7,
  product_name: "Classic Tee",
  product_slug: "classic-tee",
  user_id: 12,
  user_name: "Nimal Perera",
  user_email: "nimal@furzy.dev",
  rating: 4,
  title: "Good quality",
  comment: "The fabric feels great.",
  status: "pending",
  created_at: "2026-11-05T10:00:00Z",
  updated_at: "2026-11-05T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminReviews />
    </MemoryRouter>
  );
}

describe("AdminReviews", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminReviews.mockResolvedValue({
      reviews: [REVIEW],
      total: 1,
    });
    updateAdminReviewStatus.mockResolvedValue({
      ...REVIEW,
      status: "published",
    });
    deleteAdminReview.mockResolvedValue();
  });

  it("lists pending reviews with product and customer context", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Reviews" })
    ).toBeInTheDocument();
    expect(screen.getByText("Classic Tee")).toBeInTheDocument();
    expect(
      screen.getByText("Nimal Perera · nimal@furzy.dev")
    ).toBeInTheDocument();
    expect(screen.getByText("Good quality")).toBeInTheDocument();
    expect(
      screen.getByText("The fabric feels great.")
    ).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Classic Tee" })
    ).toHaveAttribute("href", "/admin/products/7/edit");
  });

  it("approves and rejects a review", async () => {
    renderPage();
    await screen.findByText("Classic Tee");

    fireEvent.click(
      screen.getByRole("button", { name: "Approve" })
    );

    await waitFor(() => {
      expect(updateAdminReviewStatus).toHaveBeenCalledWith(
        1,
        "published"
      );
    });
    expect(
      await screen.findByText("Review published.")
    ).toBeInTheDocument();

    fireEvent.click(
      await screen.findByRole("button", { name: "Reject" })
    );

    await waitFor(() => {
      expect(updateAdminReviewStatus).toHaveBeenCalledWith(
        1,
        "rejected"
      );
    });
  });

  it("filters by status and deletes a review", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();
    await screen.findByText("Classic Tee");

    fireEvent.change(
      screen.getByLabelText("Filter by status"),
      { target: { value: "pending" } }
    );

    await waitFor(() => {
      expect(getAdminReviews).toHaveBeenCalledWith({
        page: 1,
        limit: 20,
        status: "pending",
        rating: undefined,
        search: undefined,
      });
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Delete" })
    );

    await waitFor(() => {
      expect(deleteAdminReview).toHaveBeenCalledWith(1);
    });
    expect(
      await screen.findByText("Review deleted.")
    ).toBeInTheDocument();
  });
});
