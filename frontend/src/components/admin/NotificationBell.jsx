import { useEffect, useState } from "react";
import { FiBell } from "react-icons/fi";
import { Link } from "react-router-dom";
import { getAdminNotificationUnreadCount } from "../../api/adminNotifications";
import { NOTIFICATIONS_UPDATED_EVENT } from "../../utils/notifications";

function NotificationBell() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      getAdminNotificationUnreadCount()
        .then((value) => {
          if (!cancelled) setCount(value);
        })
        .catch(() => {});
    };

    load();
    const interval = setInterval(load, 60000);
    window.addEventListener(
      NOTIFICATIONS_UPDATED_EVENT,
      load
    );

    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener(
        NOTIFICATIONS_UPDATED_EVENT,
        load
      );
    };
  }, []);

  const label =
    count > 0
      ? `Admin notifications, ${count} unread`
      : "Admin notifications";

  return (
    <Link
      to="/admin/notifications"
      aria-label={label}
      className="relative border border-gray-700 text-gray-300 px-3 py-2 rounded-lg hover:border-cyan-400 hover:text-cyan-400 transition"
    >
      <FiBell aria-hidden="true" />

      {count > 0 && (
        <span className="absolute -top-1.5 -right-1.5 min-w-5 h-5 px-1 rounded-full bg-cyan-400 text-black text-[10px] font-bold flex items-center justify-center">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  );
}

export default NotificationBell;
