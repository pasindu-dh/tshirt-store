import { FiHeart } from "react-icons/fi";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { imageUrl } from "../api/client";
import useAuth from "../hooks/useAuth";
import useWishlist from "../hooks/useWishlist";

function ProductCard({ product }) {
  const { user } = useAuth();
  const { isWishlisted, toggleWishlist } = useWishlist();
  const location = useLocation();
  const navigate = useNavigate();
  const wished = isWishlisted(product.id);

  const totalStock = product.variants.reduce(
    (sum, variant) => sum + variant.stock,
    0
  );
  const outOfStock = totalStock === 0;

  const handleWishlist = async (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (!user) {
      navigate("/login", { state: { from: location.pathname } });
      return;
    }

    try {
      await toggleWishlist(product);
    } catch {
      // The wishlist provider exposes the error to the wishlist page.
    }
  };

  return (
    <div className="relative bg-[#111827] rounded-2xl overflow-hidden hover:scale-105 hover:shadow-xl transition duration-300">
      <button
        type="button"
        onClick={handleWishlist}
        aria-label={
          wished
            ? `Remove ${product.name} from wishlist`
            : `Add ${product.name} to wishlist`
        }
        aria-pressed={wished}
        className={`absolute top-3 right-3 z-10 rounded-full p-2 text-lg backdrop-blur-md transition ${
          wished
            ? "bg-red-500/20 text-red-400"
            : "bg-black/50 text-white hover:text-red-400"
        }`}
      >
        <FiHeart fill={wished ? "currentColor" : "none"} />
      </button>

      <Link
        to={`/product/${product.slug}`}
        aria-label={`View ${product.name}`}
      >
        <img
          src={imageUrl(product.image)}
          alt={product.name}
          className="w-full h-72 object-cover"
        />
      </Link>

      <div className="p-5">
        {product.category && (
          <p className="text-xs uppercase tracking-wide text-cyan-400">
            {product.category.name}
          </p>
        )}

        <Link to={`/product/${product.slug}`}>
          <h3 className="text-xl font-semibold mt-1 hover:text-cyan-300 transition">
            {product.name}
          </h3>
        </Link>

        <p className="text-gray-400 mt-1">LKR {product.price}</p>

        {outOfStock && (
          <p className="text-sm text-red-400 mt-2">Out of stock</p>
        )}

        <Link
          to={`/product/${product.slug}`}
          className="mt-4 block text-center w-full bg-cyan-400 text-black py-2 rounded-lg hover:bg-cyan-300 transition"
        >
          View product
        </Link>
      </div>
    </div>
  );
}

export default ProductCard;
