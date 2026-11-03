import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { imageUrl } from "../api/client";
import { getOrder } from "../api/orders";
import OrderStatusBadge from "../components/OrderStatusBadge";
import { getApiError } from "../utils/errors";

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function OrderDetail({ orderId }) {
  const location = useLocation();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getOrder(orderId)
      .then((data) => {
        if (!cancelled) setOrder(data);
      })
      .catch((requestError) => {
        if (cancelled) return;

        if (requestError.response?.status === 404) {
          setNotFound(true);
        } else {
          setError(
            getApiError(requestError, "Could not load this order.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  if (loading) {
    return (
      <p className="min-h-screen px-6 pt-20 text-center text-gray-400">
        Loading order...
      </p>
    );
  }

  if (notFound) {
    return (
      <div className="min-h-screen px-6 pt-20 text-center">
        <h1 className="text-4xl font-bold">Order not found</h1>
        <p className="text-gray-400 mt-4">
          This order does not exist or belongs to another account.
        </p>
        <Link
          to="/orders"
          className="inline-block mt-8 bg-cyan-400 text-black px-6 py-2 rounded-lg"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen px-6 pt-20 text-center">
        <p className="text-red-400">{error}</p>
        <Link
          to="/orders"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  if (!order) return null;

  const justPlaced = location.state?.justPlaced;

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-10">
      <div className="max-w-4xl mx-auto">
        {justPlaced && (
          <div className="bg-green-500/10 border border-green-500/40 rounded-2xl p-5 text-center">
            <h2 className="text-xl font-semibold text-green-400">
              Order placed successfully
            </h2>
            <p className="text-sm text-gray-300 mt-2">
              Thank you, {order.contact_name}. We have received your
              order and will process it shortly.
            </p>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-8">
          <div>
            <h1 className="text-3xl font-bold">Order #{order.id}</h1>
            <p className="text-sm text-gray-400 mt-1">
              Placed {formatDate(order.created_at)}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <OrderStatusBadge status={order.status} />
            <span className="text-sm text-gray-400 capitalize">
              Payment: {order.payment_status}
            </span>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1.3fr_0.7fr] gap-6 mt-8">
          <div className="space-y-6">
            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-4">Items</h2>

              <div className="space-y-4">
                {order.items.map((item) => (
                  <div key={item.id} className="flex items-center gap-4">
                    <img
                      src={imageUrl(item.image)}
                      alt={item.product_name}
                      className="w-16 h-16 object-cover rounded"
                    />

                    <div className="flex-1">
                      <p>{item.product_name}</p>
                      <p className="text-xs text-gray-500">
                        {item.color} / {item.size} · {item.sku}
                      </p>
                      <p className="text-sm text-gray-400">
                        {item.quantity} × LKR {item.unit_price}
                      </p>
                    </div>

                    <p className="text-cyan-400">
                      LKR {item.line_total}
                    </p>
                  </div>
                ))}
              </div>

              <hr className="border-gray-800 my-5" />

              <div className="space-y-2 text-sm">
                <div className="flex justify-between text-gray-300">
                  <span>Subtotal</span>
                  <span>LKR {order.subtotal}</span>
                </div>
                <div className="flex justify-between text-gray-300">
                  <span>Shipping</span>
                  <span>LKR {order.shipping_fee}</span>
                </div>
                <div className="flex justify-between text-lg font-semibold pt-2">
                  <span>Total</span>
                  <span className="text-cyan-400">
                    LKR {order.total}
                  </span>
                </div>
              </div>
            </section>

            {order.notes && (
              <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-2">Notes</h2>
                <p className="text-sm text-gray-400 whitespace-pre-line">
                  {order.notes}
                </p>
              </section>
            )}
          </div>

          <div className="space-y-6">
            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-3">
                Shipping address
              </h2>

              <div className="text-sm text-gray-300 space-y-1">
                <p>{order.contact_name}</p>
                <p>{order.contact_email}</p>
                <p>{order.phone}</p>
                <p>{order.address_line1}</p>
                {order.address_line2 && <p>{order.address_line2}</p>}
                <p>
                  {order.city}
                  {order.postal_code ? `, ${order.postal_code}` : ""}
                </p>
                <p>{order.country}</p>
              </div>
            </section>

            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-3">Payment</h2>
              <p className="text-sm text-gray-300">
                {order.payment_method === "cod"
                  ? "Cash on Delivery"
                  : order.payment_method}
              </p>
              <p className="text-sm text-gray-400 mt-1 capitalize">
                Status: {order.payment_status}
              </p>
            </section>

            <div className="flex flex-col gap-3">
              <Link
                to="/orders"
                className="text-center px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
              >
                Back to orders
              </Link>
              <Link
                to="/shop"
                className="text-center px-5 py-2 rounded-lg bg-cyan-400 text-black font-semibold hover:bg-cyan-300"
              >
                Continue shopping
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function OrderDetailRoute() {
  const { orderId } = useParams();
  return <OrderDetail key={orderId} orderId={orderId} />;
}

export default OrderDetailRoute;
