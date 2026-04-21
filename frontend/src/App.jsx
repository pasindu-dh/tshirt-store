import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/products")
      .then(res => setProducts(res.data));
  }, []);

  return (
    <div className="bg-gradient-to-b from-[#0a0f1c] to-black text-white min-h-screen">

      {/* NAVBAR */}
      <nav className="flex justify-between items-center px-10 py-5 border-b border-gray-800">
        <h1 className="text-2xl font-bold tracking-wide">FURZY</h1>

        <ul className="hidden md:flex gap-8 text-gray-300">
          <li className="hover:text-white cursor-pointer">Home</li>
          <li className="hover:text-white cursor-pointer">Shop</li>
          <li className="hover:text-white cursor-pointer">About</li>
          <li className="hover:text-white cursor-pointer">Contact</li>
        </ul>

        <div className="text-lg">🛒</div>
      </nav>

      {/* HERO */}
      <div className="text-center py-20">
        <h1 className="text-6xl font-extrabold tracking-tight">
          BE BETTER EVERYDAY
        </h1>
        <p className="text-gray-400 mt-4">
          Premium streetwear for your lifestyle
        </p>

        <button className="mt-6 bg-white text-black px-8 py-3 text-lg hover:bg-gray-200 transition">
          Shop Now
        </button>
      </div>

      {/* PRODUCTS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 px-10 pb-16">

        {products.map((p) => (
          <div
            key={p.id}
            className="bg-[#111827] rounded-2xl overflow-hidden hover:scale-105 hover:shadow-xl transition duration-300"
          >
            {/* IMAGE */}
            <img
              src={p.image}
              alt={p.name}
              className="w-full h-72 object-cover"
            />

            {/* DETAILS */}
            <div className="p-5">
              <h3 className="text-xl font-semibold">{p.name}</h3>
              <p className="text-gray-400 mt-1">LKR {p.price}</p>

              <button className="mt-4 w-full bg-white text-black py-2 rounded-lg hover:bg-gray-300 transition">
                Add to Cart
              </button>
            </div>
          </div>
        ))}

      </div>

    </div>
  );
}

export default App;