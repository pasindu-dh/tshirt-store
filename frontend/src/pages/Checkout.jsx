function Checkout({ cart }) {

  const total = cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  return (
    <div className="min-h-screen px-10 pt-18 pb-20">

      <h1 className="text-4xl font-bold mb-6 text-center">
        Checkout
      </h1>

      {cart.map(item => (
        <div key={item.id} className="flex justify-between mb-3">
          <span>{item.name} x {item.quantity}</span>
          <span>LKR {item.price * item.quantity}</span>
        </div>
      ))}

      <hr className="my-4 border-gray-700" />

      <h2 className="text-xl mb-4">
        Total: <span className="text-cyan-400">LKR {total}</span>
      </h2>

      <button className="bg-cyan-400 text-black px-6 py-2 rounded">
        Place Order
      </button>

    </div>
  );
}

export default Checkout;