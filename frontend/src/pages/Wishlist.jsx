import { Link } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import useWishlist from "../hooks/useWishlist";

function Wishlist() {
  const { items, loading, error, reloadWishlist } = useWishlist();

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-10">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-center">My wishlist</h1>
        <p className="text-center text-gray-400 mt-2">
          Products you have saved for later.
        </p>

        {loading && items.length === 0 ? (
          <p className="mt-10 text-center text-gray-400">
            Loading your wishlist...
          </p>
        ) : error && items.length === 0 ? (
          <div className="mt-10 text-center">
            <p className="text-red-400">{error}</p>
            <button
              type="button"
              onClick={reloadWishlist}
              className="mt-4 px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
            >
              Try again
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="mt-10 text-center">
            <p className="text-gray-400">
              Your wishlist is empty. Tap the heart on a product to save
              it here.
            </p>
            <Link
              to="/shop"
              className="inline-block mt-6 bg-cyan-400 text-black px-6 py-2 rounded-lg font-semibold hover:bg-cyan-300 transition"
            >
              Browse products
            </Link>
          </div>
        ) : (
          <>
            {error && (
              <p className="mt-6 text-center text-sm text-red-400">
                {error}
              </p>
            )}
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
              {items.map((item) => (
                <ProductCard
                  key={item.product.id}
                  product={item.product}
                />
              ))}
            </div>
            <p className="text-center text-sm text-gray-500 mt-8">
              Tap the heart on a product to remove it from your
              wishlist.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default Wishlist;
