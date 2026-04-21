import { useEffect, useState } from "react";
import axios from "axios";
import Navbar from "./components/Navbar";
import Cart from "./components/Cart";

function App() {

  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");

  const [cart, setCart] = useState(() => {
    const saved = localStorage.getItem("cart");
    return saved ? JSON.parse(saved) : [];
  });

  const [loading, setLoading] = useState(true);
  const [isCartOpen, setIsCartOpen] = useState(false);

  // FETCH PRODUCTS
  useEffect(() => {
    axios.get("http://127.0.0.1:8000/products")
      .then((res) => {
        setProducts(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  // SAVE CART
  useEffect(() => {
    localStorage.setItem("cart", JSON.stringify(cart));
  }, [cart]);

  // FILTER
  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  // ADD TO CART
  const addToCart = (product) => {
    const existing = cart.find(item => item.id === product.id);

    if (existing) {
      setCart(cart.map(item =>
        item.id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, { ...product, quantity: 1 }]);
    }
  };

  return (
    <div className="bg-black text-white min-h-screen">

      {/* NAVBAR */}
      <Navbar
        setSearch={setSearch}
        cartCount={cart.length}
        openCart={() => setIsCartOpen(true)}
      />

      {/* CART */}
      <Cart
        cart={cart}
        setCart={setCart}
        isOpen={isCartOpen}
        setIsOpen={setIsCartOpen}
      />

      {/* HERO */}
      <section className="relative h-screen">

        <img
          src="/hero.jpg"
          className="absolute w-full h-full object-cover"
        />

        <div className="absolute inset-0 bg-black/60"></div>

        <div className="relative z-10 flex flex-col items-center justify-center h-full text-center px-6">
          <h1 className="text-6xl md:text-7xl font-extrabold">
            STYLE <br /> VIBE <br /> REFLECT
          </h1>

          <p className="text-gray-300 mt-4">
            Premium streetwear for your lifestyle
          </p>

          <a href="#shop">
            <button className="mt-6 bg-white text-black px-6 py-3 font-semibold hover:bg-gray-200 transition">
              SHOP NOW
            </button>
          </a>
        </div>

      </section>

      {/* FEATURED PRODUCTS */}
      <section className="px-10 py-20 bg-black">

        <h2 className="text-center text-3xl font-bold mb-4">
          DESIGNED TO DISRUPT
        </h2>

        <p className="text-center text-gray-400 max-w-2xl mx-auto mb-10">
          Luxury staples for the modern disruptor.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">

          {filteredProducts.map((p) => (
            <div key={p.id} className="group">

              <img
                src={p.image}
                className="w-full h-72 object-cover"
              />

              <div className="mt-3">
                <p className="text-sm text-gray-400">Unisex Hoodie</p>
                <h3 className="font-semibold">{p.name}</h3>
                <p className="text-gray-300">LKR {p.price}</p>

                <button
                  onClick={() => addToCart(p)}
                  className="mt-3 w-full bg-cyan-400 text-black py-2 rounded-lg hover:bg-cyan-300 transition"
                >
                  Add to Cart
                </button>
              </div>

            </div>
          ))}

        </div>

      </section>

      {/* MISSION */}
      <section className="grid md:grid-cols-2 gap-10 px-10 py-20 bg-[#020617]">

        <div className="flex flex-col justify-center">
          <h2 className="text-3xl font-bold mb-4">Our Mission</h2>

          <p className="text-gray-400 mb-6">
            Pair text with an image to focus on your chosen product or collection.
          </p>

          <button className="border border-white px-6 py-2 w-fit hover:bg-white hover:text-black transition">
            Learn More
          </button>
        </div>

        <img src="/mission.jpg" className="w-full h-[400px] object-cover" />

      </section>

      {/* VISION */}
      <section className="grid md:grid-cols-2 gap-10 px-10 py-20 bg-[#020617]">

        <img src="/vision.jpg" className="w-full h-[400px] object-cover" />

        <div className="flex flex-col justify-center">
          <h2 className="text-3xl font-bold mb-4">Our Vision</h2>

          <p className="text-gray-400 mb-6">
            Build a bold fashion identity for modern culture.
          </p>

          <button className="border border-white px-6 py-2 w-fit hover:bg-white hover:text-black transition">
            Learn More
          </button>
        </div>

      </section>

      {/* SHOP */}
      <section id="shop" className="min-h-screen px-10 py-20">
        <h2 className="text-3xl font-bold mb-10 text-center">Shop</h2>

        {loading ? (
          <p className="text-center text-gray-400">Loading products...</p>
        ) : filteredProducts.length === 0 ? (
          <p className="text-center text-gray-400">No products found 😢</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

            {filteredProducts.map((p) => (
              <div
                key={p.id}
                className="bg-[#111827] rounded-2xl overflow-hidden hover:scale-105 hover:shadow-xl transition duration-300"
              >

                <img
                  src={p.image}
                  className="w-full h-72 object-cover"
                />

                <div className="p-5">
                  <h3 className="text-xl font-semibold">{p.name}</h3>
                  <p className="text-gray-400 mt-1">LKR {p.price}</p>

                  <button
                    onClick={() => addToCart(p)}
                    className="mt-4 w-full bg-cyan-400 text-black py-2 rounded-lg hover:bg-cyan-300 transition"
                  >
                    Add to Cart
                  </button>
                </div>

              </div>
            ))}

          </div>
        )}
      </section>

    </div>
  );
}

export default App;