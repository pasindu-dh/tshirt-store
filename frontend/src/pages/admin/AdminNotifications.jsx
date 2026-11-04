import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getAdminNotifications,
  markAdminNotificationRead,
  markAllAdminNotificationsRead,
} from "../../api/adminNotifications";
import { getApiError } from "../../utils/errors";
import {
  NOTIFICATION_TYPE_LABELS,
  announceNotificationsUpdated,
} from "../../utils/notifications";

const PAGE_SIZE = 20;

const TYPE_CLASSES = {
  new_order: "text-cyan-400",
  new_return: "text-yellow-400",
  low_stock: "text-red-400",
};

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function AdminNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [markingId, setMarkingId] = useState(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getAdminNotifications({
      page,
      limit: PAGE_SIZE,
      unread_only: unreadOnly || undefined,
    })
      .then((result) => {
        if (cancelled) return;

        setNotifications(result.notifications);
        setTotal(result.total);
        setError("");
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(
              requestError,
              "Could not load notifications."
            )
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, unreadOnly, refreshKey]);

  const refresh = () => {
    setRefreshKey((current) => current + 1);
    announceNotificationsUpdated();
  };

  const handleMarkRead = async (notificationId) => {
    setMarkingId(notificationId);
    setError("");
    setMessage("");

    try {
      await markAdminNotificationRead(notificationId);
      refresh();
      setMessage("Notification marked as read.");
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not update the notification."
        )
      );
    } finally {
      setMarkingId(null);
    }
  };

  const handleMarkAll = async () => {
    setMarkingAll(true);
    setError("");
    setMessage("");

    try {
      const result = await markAllAdminNotificationsRead();

      if (result.updated > 0) {
        setPage(1);
      }

      refresh();
      setMessage(
        result.updated > 0
          ? `${result.updated} notification${
              result.updated === 1 ? "" : "s"
            } marked as read.`
          : "No unread notifications."
      );
    } catch (requestError) {
      setError(
        getApiError(
          requestError,
          "Could not mark notifications as read."
        )
      );
    } finally {
      setMarkingAll(false);
    }
  };

  const handleFilterChange = (event) => {
    setUnreadOnly(event.target.value === "unread");
    setPage(1);
    setLoading(true);
    setError("");
    setMessage("");
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">Notifications</h2>
          <p className="text-gray-400 text-sm mt-1">
            {total} notification{total === 1 ? "" : "s"}
            {unreadOnly ? " unread" : " total"}
          </p>
        </div>

        <button
          type="button"
          onClick={handleMarkAll}
          disabled={markingAll}
          className="border border-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm font-semibold hover:border-cyan-400 hover:text-cyan-400 disabled:opacity-50"
        >
          {markingAll ? "Updating..." : "Mark all read"}
        </button>
      </div>

      <div className="mt-6">
        <select
          value={unreadOnly ? "unread" : "all"}
          onChange={handleFilterChange}
          aria-label="Filter notifications"
          className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
        >
          <option value="all">All notifications</option>
          <option value="unread">Unread only</option>
        </select>
      </div>

      {message && (
        <p className="text-sm text-green-400 mt-3">{message}</p>
      )}

      {error ? (
        <div className="mt-10 text-center">
          <p className="text-red-400">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setError("");
              setRefreshKey((current) => current + 1);
            }}
            className="mt-4 px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
          >
            Try again
          </button>
        </div>
      ) : loading ? (
        <p className="mt-8 text-gray-400">
          Loading notifications...
        </p>
      ) : notifications.length === 0 ? (
        <div className="mt-6 bg-[#020617] border border-gray-800 rounded-2xl p-8 text-center">
          <p className="text-gray-400">
            {unreadOnly
              ? "No unread notifications."
              : "No notifications yet."}
          </p>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {notifications.map((notification) => (
            <article
              key={notification.id}
              className={`border rounded-2xl p-4 ${
                notification.is_read
                  ? "border-gray-800 bg-[#020617]"
                  : "border-cyan-500/40 bg-cyan-500/5"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    {!notification.is_read && (
                      <span
                        aria-label="Unread"
                        className="w-2 h-2 rounded-full bg-cyan-400"
                      />
                    )}
                    <p
                      className={`text-xs font-semibold ${
                        TYPE_CLASSES[
                          notification.notification_type
                        ] ?? "text-gray-400"
                      }`}
                    >
                      {NOTIFICATION_TYPE_LABELS[
                        notification.notification_type
                      ] ?? notification.notification_type}
                    </p>
                  </div>
                  <h3 className="font-semibold mt-1">
                    {notification.title}
                  </h3>
                  <p className="text-sm text-gray-400 mt-1">
                    {notification.message}
                  </p>
                  <p className="text-xs text-gray-600 mt-2">
                    {formatDate(notification.created_at)}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {notification.link && (
                    <Link
                      to={notification.link}
                      className="text-sm text-cyan-400 hover:text-cyan-300"
                    >
                      View
                    </Link>
                  )}
                  {!notification.is_read && (
                    <button
                      type="button"
                      onClick={() =>
                        handleMarkRead(notification.id)
                      }
                      disabled={markingId === notification.id}
                      className="text-sm text-gray-400 hover:text-cyan-400 disabled:opacity-50"
                    >
                      {markingId === notification.id
                        ? "Updating..."
                        : "Mark read"}
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            type="button"
            disabled={page === 1}
            onClick={() => {
              setLoading(true);
              setPage((current) => current - 1);
            }}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => {
              setLoading(true);
              setPage((current) => current + 1);
            }}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default AdminNotifications;
