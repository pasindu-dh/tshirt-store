import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getProducts } from "../api/products";
import ProductCard from "../components/ProductCard";

const FEATURED_LIMIT = 6;

function Home() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getProducts({ page: 1, limit: FEATURED_LIMIT })
      .then((result) => {
        if (!cancelled) setProducts(result.products);
      })
      .catch(() => {
        if (!cancelled) {
          setError("Could not load products. Is the backend running?");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      {/* HERO */}
      <section id="home" className="relative h-screen">
        <img
          src="/hero.png"
          alt=""
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
            type="button"
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

      {/* FEATURED PRODUCTS */}
      <section id="shop" className="min-h-screen px-6 md:px-10 py-20">
        <div className="text-center">
          <h2 className="text-3xl font-bold">Shop</h2>
          <p className="text-gray-400 mt-2">
            Fresh picks from the latest collection.
          </p>
        </div>

        {loading ? (
          <p className="text-center text-gray-400 mt-10">
            Loading products...
          </p>
        ) : error ? (
          <p className="text-center text-red-400 mt-10">{error}</p>
        ) : products.length === 0 ? (
          <p className="text-center text-gray-400 mt-10">
            No products found 😢
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 mt-10">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}

        <div className="text-center mt-12">
          <Link
            to="/shop"
            className="inline-block px-8 py-3 rounded-full border border-cyan-400 text-cyan-400 font-semibold hover:bg-cyan-400 hover:text-black transition"
          >
            View all products
          </Link>
        </div>
      </section>
    </>
  );
}

export default Home;
