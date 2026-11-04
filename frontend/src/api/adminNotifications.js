import client from "./client";

export async function getAdminNotifications(params = {}) {
  const { data, headers } = await client.get(
    "/admin/notifications",
    { params }
  );

  return {
    notifications: data,
    total: Number(headers["x-total-count"] ?? data.length),
  };
}

export async function getAdminNotificationUnreadCount() {
  const { data } = await client.get(
    "/admin/notifications/unread-count"
  );
  return data.count;
}

export async function markAdminNotificationRead(notificationId) {
  const { data } = await client.patch(
    `/admin/notifications/${notificationId}/read`
  );
  return data;
}

export async function markAllAdminNotificationsRead() {
  const { data } = await client.post(
    "/admin/notifications/read-all"
  );
  return data;
}
