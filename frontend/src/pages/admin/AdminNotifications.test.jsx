import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminNotifications from "./AdminNotifications";
import {
  getAdminNotifications,
  markAdminNotificationRead,
  markAllAdminNotificationsRead,
} from "../../api/adminNotifications";

vi.mock("../../api/adminNotifications", () => ({
  getAdminNotifications: vi.fn(),
  markAdminNotificationRead: vi.fn(),
  markAllAdminNotificationsRead: vi.fn(),
}));

const NOTIFICATION = {
  id: 9,
  notification_type: "new_order",
  title: "New order #44",
  message: "Nimal placed an order for LKR 5000.",
  link: "/admin/orders/44",
  is_read: false,
  read_at: null,
  created_at: "2026-11-04T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminNotifications />
    </MemoryRouter>
  );
}

describe("AdminNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminNotifications.mockResolvedValue({
      notifications: [NOTIFICATION],
      total: 1,
    });
    markAdminNotificationRead.mockResolvedValue({
      ...NOTIFICATION,
      is_read: true,
      read_at: "2026-11-04T11:00:00Z",
    });
    markAllAdminNotificationsRead.mockResolvedValue({
      updated: 1,
    });
  });

  it("lists notifications and marks one as read", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Notifications",
      })
    ).toBeInTheDocument();
    expect(screen.getByText("New order")).toBeInTheDocument();
    expect(screen.getByText("New order #44")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Nimal placed an order for LKR 5000."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View" })
    ).toHaveAttribute("href", "/admin/orders/44");
    expect(
      getAdminNotifications
    ).toHaveBeenCalledWith({
      page: 1,
      limit: 20,
      unread_only: undefined,
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Mark read" })
    );

    await waitFor(() => {
      expect(markAdminNotificationRead).toHaveBeenCalledWith(9);
    });
    expect(
      await screen.findByText(
        "Notification marked as read."
      )
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(getAdminNotifications.mock.calls.length).toBeGreaterThan(
        1
      );
    });
  });

  it("marks all notifications as read", async () => {
    renderPage();
    await screen.findByText("New order #44");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Mark all read",
      })
    );

    await waitFor(() => {
      expect(
        markAllAdminNotificationsRead
      ).toHaveBeenCalledTimes(1);
    });
    expect(
      await screen.findByText(
        "1 notification marked as read."
      )
    ).toBeInTheDocument();
  });
});
