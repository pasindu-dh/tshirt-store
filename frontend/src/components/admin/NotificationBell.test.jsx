import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import NotificationBell from "./NotificationBell";
import { getAdminNotificationUnreadCount } from "../../api/adminNotifications";

vi.mock("../../api/adminNotifications", () => ({
  getAdminNotificationUnreadCount: vi.fn(),
}));

function renderBell() {
  return render(
    <MemoryRouter>
      <NotificationBell />
    </MemoryRouter>
  );
}

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the unread count and links to notifications", async () => {
    getAdminNotificationUnreadCount.mockResolvedValue(3);

    renderBell();

    const link = await screen.findByRole("link", {
      name: "Admin notifications, 3 unread",
    });

    expect(link).toHaveAttribute(
      "href",
      "/admin/notifications"
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("hides the badge when there are no unread items", async () => {
    getAdminNotificationUnreadCount.mockResolvedValue(0);

    renderBell();

    expect(
      await screen.findByRole("link", {
        name: "Admin notifications",
      })
    ).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
