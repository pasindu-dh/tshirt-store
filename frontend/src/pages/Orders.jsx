import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { imageUrl } from "../api/client";
import { getOrders } from "../api/orders";
import OrderStatusBadge from "../components/OrderStatusBadge";
import { getApiError } from "../utils/errors";

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getOrders()
      .then((data) => {
        if (!cancelled) {
          setOrders(data);
          setError("");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(
            getApiError(requestError, "Could not load your orders.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const retry = () => {
    setLoading(true);
    setError("");
    setRefreshKey((current) => current + 1);
  };

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-10">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-center">My orders</h1>
        <p className="text-center text-gray-400 mt-2">
          Track and review your FURZY orders.
        </p>

        {loading ? (
          <p className="mt-10 text-center text-gray-400">
            Loading orders...
          </p>
        ) : error ? (
          <div className="mt-10 text-center">
            <p className="text-red-400">{error}</p>
            <button
              type="button"
              onClick={retry}
              className="mt-4 px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
            >
              Try again
            </button>
          </div>
        ) : orders.length === 0 ? (
          <div className="mt-10 text-center">
            <p className="text-gray-400">
              You have not placed any orders yet.
            </p>
            <Link
              to="/shop"
              className="inline-block mt-6 bg-cyan-400 text-black px-6 py-2 rounded-lg hover:bg-cyan-300 transition"
            >
              Start shopping
            </Link>
          </div>
        ) : (
          <div className="mt-8 space-y-4">
            {orders.map((order) => {
              const itemCount = order.items.reduce(
                (sum, item) => sum + item.quantity,
                0
              );
              const firstItem = order.items[0];

              return (
                <Link
                  key={order.id}
                  to={`/orders/${order.id}`}
                  className="block bg-[#020617] border border-gray-800 rounded-2xl p-5 hover:border-cyan-400/60 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                      <p className="font-semibold">
                        Order #{order.id}
                      </p>
                      <p className="text-sm text-gray-400 mt-1">
                        {formatDate(order.created_at)} · {itemCount}{" "}
                        item{itemCount === 1 ? "" : "s"}
                      </p>
                    </div>

                    <div className="flex items-center gap-4">
                      <OrderStatusBadge status={order.status} />
                      <span className="text-cyan-400 font-semibold">
                        LKR {order.total}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 mt-4">
                    {firstItem?.image && (
                      <img
                        src={imageUrl(firstItem.image)}
                        alt=""
                        className="w-12 h-12 object-cover rounded"
                      />
                    )}
                    <p className="text-sm text-gray-400">
                      {firstItem?.product_name}
                      {order.items.length > 1
                        ? ` + ${order.items.length - 1} more`
                        : ""}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default Orders;
