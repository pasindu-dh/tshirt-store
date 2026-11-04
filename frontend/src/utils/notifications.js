export const NOTIFICATIONS_UPDATED_EVENT =
  "furzy:notifications-updated";

export const NOTIFICATION_TYPE_LABELS = {
  new_order: "New order",
  new_return: "Return request",
  low_stock: "Inventory alert",
};

export function announceNotificationsUpdated() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new Event(NOTIFICATIONS_UPDATED_EVENT)
    );
  }
}
