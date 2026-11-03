import { imageUrl } from "../api/client";
import useCart from "../hooks/useCart";

function ProductCard({ product }) {
  const { addToCart } = useCart();

  return (
    <div className="bg-[#111827] rounded-2xl overflow-hidden hover:scale-105 hover:shadow-xl transition duration-300">
      <img
        src={imageUrl(product.image)}
        alt={product.name}
        className="w-full h-72 object-cover"
      />

      <div className="p-5">
        <h3 className="text-xl font-semibold">{product.name}</h3>
        <p className="text-gray-400 mt-1">LKR {product.price}</p>

        <button
          type="button"
          onClick={() => addToCart(product)}
          className="mt-4 w-full bg-cyan-400 text-black py-2 rounded-lg hover:bg-cyan-300 transition"
        >
          Add to Cart
        </button>
      </div>
    </div>
  );
}

export default ProductCard;
