function Cart({ cart, setCart, isOpen, setIsOpen }) {

  // REMOVE ITEM
  const removeItem = (index) => {
    const newCart = cart.filter((_, i) => i !== index);
    setCart(newCart);
  };

  // INCREASE
  const increaseQty = (id) => {
    setCart(cart.map(item =>
      item.id === id
        ? { ...item, quantity: item.quantity + 1 }
        : item
    ));
  };

  // DECREASE
  const decreaseQty = (id) => {
    setCart(
      cart
        .map(item =>
          item.id === id
            ? { ...item, quantity: item.quantity - 1 }
            : item
        )
        .filter(item => item.quantity > 0)
    );
  };

  // TOTAL
  const total = cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  return (
    <div
      className={`fixed top-0 right-0 h-full w-80 bg-[#020617] text-white shadow-lg z-50 transform transition-transform duration-300 ${
        isOpen ? "translate-x-0" : "translate-x-full"
      }`}
    >

      {/* HEADER */}
      <div className="flex justify-between items-center p-4 border-b border-gray-800">
        <h2 className="text-xl font-bold">Cart</h2>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      {/* ITEMS */}
      <div className="p-4 space-y-4 overflow-y-auto h-[65%]">

        {cart.length === 0 ? (
          <p className="text-gray-400 text-center">Cart is empty</p>
        ) : (
          cart.map((item, index) => (
            <div
              key={index}
              className="flex gap-3 items-center bg-[#111827] p-3 rounded-lg"
            >

              {/* IMAGE */}
              <img
                src={item.image}
                alt={item.name}
                className="w-16 h-16 object-cover rounded"
              />

              {/* DETAILS */}
              <div className="flex-1">
                <h3 className="text-sm">{item.name}</h3>
                <p className="text-gray-400 text-sm">
                  LKR {item.price}
                </p>

                {/* QUANTITY CONTROLS */}
                <div className="flex items-center gap-2 mt-2">

                  <button
                    onClick={() => decreaseQty(item.id)}
                    className="px-2 bg-gray-700 rounded"
                  >
                    -
                  </button>

                  <span>{item.quantity}</span>

                  <button
                    onClick={() => increaseQty(item.id)}
                    className="px-2 bg-gray-700 rounded"
                  >
                    +
                  </button>

                </div>
              </div>

              {/* REMOVE BUTTON */}
              <button
                onClick={() => removeItem(index)}
                className="text-red-400 text-sm"
              >
                ✕
              </button>

            </div>
          ))
        )}

      </div>

      {/* FOOTER */}
      <div className="p-4 border-t border-gray-800">
        <p className="mb-3">
          Total: <span className="text-cyan-400">LKR {total}</span>
        </p>

        <button
          onClick={() => window.location.href = "/checkout"}
          className="w-full bg-cyan-400 text-black py-2 rounded-lg hover:bg-cyan-300 transition"
        >
          Checkout
        </button>
      </div>

    </div>
  );
}

export default Cart;