import { useEffect, useState } from "react";
import axios from "axios";
import Navbar from "./components/Navbar";
import Cart from "./components/Cart";
import ParticleBackground from "./components/ParticleBackground";
import { Routes, Route } from "react-router-dom";
import About from "./pages/About";
import Contact from "./pages/Contact";
import { useNavigate } from "react-router-dom";


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
    axios.get("http://127.0.0.1:8005/products")
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

  // ✅ SCROLL FUNCTION
  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    section?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <>
      <ParticleBackground />

      <div className="relative z-10 bg-black text-white min-h-screen pt-20">

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

        <Routes>

          {/* HOME PAGE */}
          <Route path="/" element={
            <>
              {/* HERO */}
              <section id="home" className="relative h-screen">

                <img
                  src="/hero.png"
                  className="absolute w-full h-full object-cover -z-10 opacity-20"
                />

                <div className="absolute inset-0 bg-black/40 z-0"></div>

                <div className="relative z-10 flex flex-col items-center justify-center h-full text-center px-6">

                  <div className="absolute w-72 h-72 bg-cyan-500 rounded-full blur-[140px] opacity-20 top-20 left-20 -z-10"></div>
                  <div className="absolute w-72 h-72 bg-blue-500 rounded-full blur-[140px] opacity-20 bottom-20 right-20 -z-10"></div>

                  <h1 className="text-6xl md:text-7xl font-extrabold">
                    STYLE <br /> VIBE <br /> REFLECT
                  </h1>

                  <p className="text-gray-300 mt-4">
                    Premium streetwear for your lifestyle
                  </p>

                  <button
                    onClick={() => navigate("/shop")}
                    className="mt-8 px-10 py-4 rounded-full font-semibold text-black 
                    bg-gradient-to-r from-cyan-400 to-blue-500 
                    shadow-[0_0_25px_rgba(34,211,238,0.7)] 
                    transition-all duration-300 
                    hover:scale-110 
                    hover:shadow-[0_0_40px_rgba(34,211,238,1)]"
                  >
                    SHOP NOW
                  </button>

                </div>
              </section>

              {/* SHOP */}
              <section id="shop" className="min-h-screen px-10 py-20">

                <h2 className="text-3xl font-bold mb-10 text-center">
                  Shop
                </h2>

                {loading ? (
                  <p className="text-center text-gray-400">
                    Loading products...
                  </p>
                ) : filteredProducts.length === 0 ? (
                  <p className="text-center text-gray-400">
                    No products found 😢
                  </p>
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
            </>
          } />

        <Route path="/shop" element={
          <section className="min-h-screen px-10 pb-20">        

              <h2 className="text-3xl font-bold mb-10 text-center">
                Shop
              </h2>

              {loading ? (
                <p className="text-center text-gray-400">
                  Loading products...
                </p>
              ) : filteredProducts.length === 0 ? (
                <p className="text-center text-gray-400">
                  No products found 😢
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

                  {filteredProducts.map((p) => (
                    <div key={p.id} className="bg-[#111827] rounded-2xl overflow-hidden">

                      <img src={p.image} className="w-full h-72 object-cover" />

                      <div className="p-5">
                        <h3 className="text-xl font-semibold">{p.name}</h3>
                        <p className="text-gray-400 mt-1">LKR {p.price}</p>

                        <button
                          onClick={() => addToCart(p)}
                          className="mt-4 w-full bg-cyan-400 text-black py-2 rounded-lg"
                        >
                          Add to Cart
                        </button>
                      </div>

                    </div>
                  ))}

                </div>
              )}

            </section>
          } />

          {/* ABOUT PAGE */}
          <Route path="/about" element={<About />} />

          {/* CONTACT PAGE */}
          <Route path="/contact" element={<Contact />} />

        </Routes>

      </div>
    </>
  );
};
export default App;