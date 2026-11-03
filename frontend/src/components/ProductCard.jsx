import { Link } from "react-router-dom";
import { imageUrl } from "../api/client";

function ProductCard({ product }) {
  const totalStock = product.variants.reduce(
    (sum, variant) => sum + variant.stock,
    0
  );
  const outOfStock = totalStock === 0;

  return (
    <div className="bg-[#111827] rounded-2xl overflow-hidden hover:scale-105 hover:shadow-xl transition duration-300">
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
