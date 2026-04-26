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

  // FILTER PRODUCTS
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

  // SCROLL FUNCTION (used in hero button)
  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    section?.scrollIntoView({ behavior: "smooth" });
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

      {/* HOME / HERO */}
      <section id="home" className="relative h-screen">

        <img
          src="/hero.png"
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

          <button
            onClick={() => scrollToSection("shop")}
            className="mt-6 bg-white text-black px-6 py-3 font-semibold hover:bg-gray-200 transition"
          >
            SHOP NOW
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

      {/* ABOUT */}
      <section id="about" className="px-10 py-20 bg-[#020617] text-center">
        <h2 className="text-3xl font-bold mb-4">About Us</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          We create modern streetwear that reflects your personality and lifestyle.
          Designed for bold individuals who want to stand out.
        </p>
      </section>

      {/* CONTACT */}
      <section id="contact" className="px-10 py-20 bg-[#020617] text-center">
        <h2 className="text-3xl font-bold mb-4">Contact Us</h2>
        <p className="text-gray-400 mb-6">
          Have questions? Reach out to us anytime.
        </p>

        <button className="bg-cyan-400 text-black px-6 py-3 rounded-lg hover:bg-cyan-300 transition">
          Contact Now
        </button>
      </section>

    </div>
  );
}

export default App;