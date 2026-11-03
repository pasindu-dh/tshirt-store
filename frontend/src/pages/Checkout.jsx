import { Link } from "react-router-dom";
import { imageUrl } from "../api/client";
import useCart from "../hooks/useCart";

function Checkout() {
  const { cart, cartTotal } = useCart();

  if (cart.length === 0) {
    return (
      <div className="min-h-screen px-6 pb-20 pt-20 flex flex-col items-center text-center">
        <h1 className="text-4xl font-bold mb-4">Checkout</h1>
        <p className="text-gray-400">Your cart is empty.</p>

        <Link
          to="/shop"
          className="mt-8 bg-cyan-400 text-black px-6 py-2 rounded-lg hover:bg-cyan-300 transition"
        >
          Browse products
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-10">
      <h1 className="text-4xl font-bold mb-10 text-center">Checkout</h1>

      <div className="max-w-2xl mx-auto">
        <div className="bg-[#020617] border border-gray-800 rounded-2xl p-6 space-y-4">
          {cart.map((item) => {
            const variantLabel = [item.color, item.size]
              .filter(Boolean)
              .join(" / ");

            return (
              <div key={item.key} className="flex items-center gap-4">
                <img
                  src={imageUrl(item.image)}
                  alt={item.name}
                  className="w-16 h-16 object-cover rounded"
                />

                <div className="flex-1">
                  <p>{item.name}</p>

                  {variantLabel && (
                    <p className="text-xs text-gray-500">{variantLabel}</p>
                  )}

                  <p className="text-sm text-gray-400">
                    Qty: {item.quantity}
                  </p>
                </div>

                <p className="text-cyan-400">
                  LKR {item.price * item.quantity}
                </p>
              </div>
            );
          })}

          <hr className="border-gray-800" />

          <div className="flex justify-between text-lg font-semibold">
            <span>Total</span>
            <span className="text-cyan-400">LKR {cartTotal}</span>
          </div>
        </div>

        <p className="text-center text-gray-400 text-sm mt-6">
          Online ordering is coming soon.
        </p>

        <button
          type="button"
          disabled
          className="mt-4 w-full bg-cyan-400 text-black py-3 rounded-lg font-semibold opacity-50 cursor-not-allowed"
        >
          Place Order
        </button>

        <div className="text-center mt-6">
          <Link to="/shop" className="text-cyan-400 hover:text-cyan-300">
            Continue shopping
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Checkout;
