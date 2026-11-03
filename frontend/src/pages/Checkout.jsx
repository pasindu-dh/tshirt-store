import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { imageUrl } from "../api/client";
import { createOrder } from "../api/orders";
import useAuth from "../hooks/useAuth";
import useCart from "../hooks/useCart";
import { getApiError } from "../utils/errors";

function Checkout() {
  const { user } = useAuth();
  const {
    cart,
    cartTotal,
    shippingFee,
    grandTotal,
    cartLoading,
    clearCart,
  } = useCart();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    contact_name: user?.name ?? "",
    phone: "",
    address_line1: "",
    address_line2: "",
    city: "",
    postal_code: "",
    country: "Sri Lanka",
    notes: "",
    payment_method: "cod",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const order = await createOrder(form);

      try {
        await clearCart();
      } catch {
        // The server clears the cart when the order is created.
      }

      navigate(`/orders/${order.id}`, {
        state: { justPlaced: true },
      });
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not place your order.")
      );
      setSubmitting(false);
    }
  };

  if (cartLoading) {
    return (
      <p className="min-h-screen px-6 pt-20 text-center text-gray-400">
        Loading your cart...
      </p>
    );
  }

  if (cart.length === 0) {
    return (
      <div className="min-h-screen px-6 pt-20 text-center">
        <h1 className="text-4xl font-bold">Checkout</h1>
        <p className="text-gray-400 mt-4">Your cart is empty.</p>
        <Link
          to="/shop"
          className="inline-block mt-8 bg-cyan-400 text-black px-6 py-2 rounded-lg hover:bg-cyan-300 transition"
        >
          Browse products
        </Link>
      </div>
    );
  }

  const inputClass =
    "mt-1 w-full p-3 rounded-lg bg-black border border-gray-700 outline-none focus:border-cyan-400";
  const labelClass = "block";

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-10">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold text-center">Checkout</h1>
        <p className="text-center text-gray-400 mt-2">
          Complete your details to place the order.
        </p>

        {error && (
          <p className="mt-6 text-red-400 text-sm text-center">{error}</p>
        )}

        <form
          onSubmit={handleSubmit}
          className="grid lg:grid-cols-[1.2fr_0.8fr] gap-8 mt-8"
        >
          <div className="space-y-6">
            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4">
              <h2 className="text-lg font-semibold">Contact</h2>

              <div className="grid sm:grid-cols-2 gap-4">
                <label className={labelClass}>
                  <span className="text-sm text-gray-300">
                    Full name
                  </span>
                  <input
                    value={form.contact_name}
                    onChange={(event) =>
                      updateField("contact_name", event.target.value)
                    }
                    required
                    minLength={2}
                    className={inputClass}
                  />
                </label>

                <label className={labelClass}>
                  <span className="text-sm text-gray-300">Email</span>
                  <input
                    value={user?.email ?? ""}
                    readOnly
                    className={`${inputClass} opacity-70`}
                  />
                </label>
              </div>

              <label className={labelClass}>
                <span className="text-sm text-gray-300">Phone</span>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={(event) =>
                    updateField("phone", event.target.value)
                  }
                  required
                  minLength={5}
                  className={inputClass}
                />
              </label>
            </section>

            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4">
              <h2 className="text-lg font-semibold">
                Shipping address
              </h2>

              <label className={labelClass}>
                <span className="text-sm text-gray-300">
                  Address line 1
                </span>
                <input
                  value={form.address_line1}
                  onChange={(event) =>
                    updateField("address_line1", event.target.value)
                  }
                  required
                  minLength={3}
                  className={inputClass}
                />
              </label>

              <label className={labelClass}>
                <span className="text-sm text-gray-300">
                  Address line 2 (optional)
                </span>
                <input
                  value={form.address_line2}
                  onChange={(event) =>
                    updateField("address_line2", event.target.value)
                  }
                  className={inputClass}
                />
              </label>

              <div className="grid sm:grid-cols-2 gap-4">
                <label className={labelClass}>
                  <span className="text-sm text-gray-300">City</span>
                  <input
                    value={form.city}
                    onChange={(event) =>
                      updateField("city", event.target.value)
                    }
                    required
                    minLength={2}
                    className={inputClass}
                  />
                </label>

                <label className={labelClass}>
                  <span className="text-sm text-gray-300">
                    Postal code (optional)
                  </span>
                  <input
                    value={form.postal_code}
                    onChange={(event) =>
                      updateField("postal_code", event.target.value)
                    }
                    className={inputClass}
                  />
                </label>
              </div>

              <label className={labelClass}>
                <span className="text-sm text-gray-300">Country</span>
                <input
                  value={form.country}
                  onChange={(event) =>
                    updateField("country", event.target.value)
                  }
                  required
                  minLength={2}
                  className={inputClass}
                />
              </label>
            </section>

            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4">
              <h2 className="text-lg font-semibold">Payment</h2>

              <label className="flex items-start gap-3 bg-black border border-cyan-500/40 rounded-xl p-4">
                <input
                  type="radio"
                  name="payment_method"
                  value="cod"
                  checked
                  readOnly
                  className="mt-1 accent-cyan-400"
                />
                <span>
                  <span className="block font-medium">
                    Cash on Delivery
                  </span>
                  <span className="block text-sm text-gray-400 mt-1">
                    Pay in cash when your order is delivered.
                  </span>
                </span>
              </label>
            </section>

            <section className="bg-[#020617] border border-gray-800 rounded-2xl p-6">
              <h2 className="text-lg font-semibold mb-3">
                Order notes (optional)
              </h2>
              <textarea
                value={form.notes}
                onChange={(event) =>
                  updateField("notes", event.target.value)
                }
                rows={3}
                aria-label="Order notes (optional)"
                className={inputClass}
              />
            </section>
          </div>

          <aside className="bg-[#020617] border border-gray-800 rounded-2xl p-6 h-fit lg:sticky lg:top-28 space-y-4">
            <h2 className="text-lg font-semibold">Order summary</h2>

            {cart.map((item) => {
              const variantLabel = [item.color, item.size]
                .filter(Boolean)
                .join(" / ");

              return (
                <div key={item.key} className="flex items-center gap-3">
                  <img
                    src={imageUrl(item.image)}
                    alt={item.name}
                    className="w-14 h-14 object-cover rounded"
                  />

                  <div className="flex-1">
                    <p className="text-sm">{item.name}</p>

                    {variantLabel && (
                      <p className="text-xs text-gray-500">
                        {variantLabel}
                      </p>
                    )}

                    <p className="text-xs text-gray-400">
                      Qty: {item.quantity}
                    </p>
                  </div>

                  <p className="text-sm text-cyan-400">
                    LKR {item.price * item.quantity}
                  </p>
                </div>
              );
            })}

            <hr className="border-gray-800" />

            <div className="flex justify-between text-sm text-gray-300">
              <span>Subtotal</span>
              <span>LKR {cartTotal}</span>
            </div>

            <div className="flex justify-between text-sm text-gray-300">
              <span>Shipping</span>
              <span>LKR {shippingFee}</span>
            </div>

            <div className="flex justify-between text-lg font-semibold">
              <span>Total</span>
              <span className="text-cyan-400">LKR {grandTotal}</span>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-cyan-400 text-black py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Placing order..." : "Place order"}
            </button>

            <Link
              to="/shop"
              className="block text-center text-sm text-gray-400 hover:text-cyan-400"
            >
              Continue shopping
            </Link>
          </aside>
        </form>
      </div>
    </div>
  );
}

export default Checkout;
