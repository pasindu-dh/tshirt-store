import { useNavigate } from "react-router-dom";
import { imageUrl } from "../api/client";
import useCart from "../hooks/useCart";

function Cart() {
  const {
    cart,
    increaseQty,
    decreaseQty,
    removeItem,
    cartTotal,
    cartLoading,
    isCartOpen,
    closeCart,
  } = useCart();

  const navigate = useNavigate();

  const goToCheckout = () => {
    closeCart();
    navigate("/checkout");
  };

  return (
    <>
      {isCartOpen && (
        <div
          onClick={closeCart}
          aria-hidden="true"
          className="fixed inset-0 bg-black/60 z-40"
        />
      )}

      <aside
        className={`fixed top-0 right-0 h-full w-full max-w-sm bg-[#020617] text-white shadow-lg z-50 flex flex-col transform transition-transform duration-300 ${
          isCartOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* HEADER */}
        <div className="flex justify-between items-center p-4 border-b border-gray-800">
          <h2 className="text-xl font-bold">Cart</h2>
          <button
            type="button"
            onClick={closeCart}
            aria-label="Close cart"
            className="text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* ITEMS */}
        <div className="flex-1 p-4 space-y-4 overflow-y-auto">
          {cartLoading && cart.length === 0 ? (
            <div className="text-center">
              <p className="text-gray-400">Loading your cart...</p>
            </div>
          ) : cart.length === 0 ? (
            <div className="text-center">
              <p className="text-gray-400">Cart is empty</p>
              <button
                type="button"
                onClick={() => {
                  closeCart();
                  navigate("/shop");
                }}
                className="mt-4 text-sm text-cyan-400 hover:text-cyan-300"
              >
                Continue shopping
              </button>
            </div>
          ) : (
            cart.map((item) => {
              const variantLabel = [item.color, item.size]
                .filter(Boolean)
                .join(" / ");
              const atMaxStock =
                item.stock != null && item.quantity >= item.stock;

              return (
                <div
                  key={item.key}
                  className="flex gap-3 items-center bg-[#111827] p-3 rounded-lg"
                >
                  {/* IMAGE */}
                  <img
                    src={imageUrl(item.image)}
                    alt={item.name}
                    className="w-16 h-16 object-cover rounded"
                  />

                  {/* DETAILS */}
                  <div className="flex-1">
                    <h3 className="text-sm">{item.name}</h3>

                    {variantLabel && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {variantLabel}
                      </p>
                    )}

                    <p className="text-gray-400 text-sm">
                      LKR {item.price}
                    </p>

                    {/* QUANTITY CONTROLS */}
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        type="button"
                        onClick={() => decreaseQty(item.key)}
                        aria-label={`Decrease ${item.name} quantity`}
                        className="px-2 bg-gray-700 rounded"
                      >
                        -
                      </button>

                      <span>{item.quantity}</span>

                      <button
                        type="button"
                        onClick={() => increaseQty(item.key)}
                        disabled={atMaxStock}
                        title={
                          atMaxStock ? "Maximum stock reached" : undefined
                        }
                        aria-label={`Increase ${item.name} quantity`}
                        className="px-2 bg-gray-700 rounded disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        +
                      </button>
                    </div>

                    {atMaxStock && (
                      <p className="text-xs text-gray-500 mt-1">
                        Maximum stock reached
                      </p>
                    )}
                  </div>

                  {/* REMOVE BUTTON */}
                  <button
                    type="button"
                    onClick={() => removeItem(item.key)}
                    aria-label={`Remove ${item.name} from cart`}
                    className="text-red-400 text-sm"
                  >
                    ✕
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* FOOTER */}
        <div className="p-4 border-t border-gray-800">
          <p className="mb-1">
            Subtotal:{" "}
            <span className="text-cyan-400">LKR {cartTotal}</span>
          </p>
          <p className="mb-3 text-xs text-gray-500">
            Shipping calculated at checkout.
          </p>

          <button
            type="button"
            onClick={goToCheckout}
            disabled={cart.length === 0 || cartLoading}
            className="w-full bg-cyan-400 text-black py-2 rounded-lg hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Checkout
          </button>
        </div>
      </aside>
    </>
  );
}

export default Cart;
