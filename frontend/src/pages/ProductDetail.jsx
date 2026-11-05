import { useEffect, useMemo, useState } from "react";
import { FiHeart } from "react-icons/fi";
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { imageUrl } from "../api/client";
import {
  getProductBySlug,
  getRelatedProducts,
} from "../api/products";
import ProductCard from "../components/ProductCard";
import ProductReviews from "../components/ProductReviews";
import useAuth from "../hooks/useAuth";
import useCart from "../hooks/useCart";
import useWishlist from "../hooks/useWishlist";
import { getCartKey } from "../utils/cart";
import { getApiError } from "../utils/errors";

const SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "3XL"];

function sortSizes(sizes) {
  return [...sizes].sort((a, b) => {
    const aIndex = SIZE_ORDER.indexOf(a.toUpperCase());
    const bIndex = SIZE_ORDER.indexOf(b.toUpperCase());

    if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
    if (aIndex === -1) return 1;
    if (bIndex === -1) return -1;
    return aIndex - bIndex;
  });
}

function ProductDetail({ slug }) {
  const { cart, addToCart, openCart } = useCart();
  const { user } = useAuth();
  const { isWishlisted, toggleWishlist } = useWishlist();
  const location = useLocation();
  const navigate = useNavigate();

  const [product, setProduct] = useState(null);
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [selectedImage, setSelectedImage] = useState(0);
  const [selectedColor, setSelectedColor] = useState("");
  const [selectedSize, setSelectedSize] = useState("");
  const [message, setMessage] = useState("");
  const [messageError, setMessageError] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    let cancelled = false;

    window.scrollTo(0, 0);

    getProductBySlug(slug)
      .then((data) => {
        if (cancelled) return;

        setProduct(data);

        if (data.variants.length > 0) {
          const defaultVariant =
            data.variants.find((variant) => variant.stock > 0) ??
            data.variants[0];

          setSelectedColor(defaultVariant.color);
          setSelectedSize(defaultVariant.size);
        }
      })
      .catch((requestError) => {
        if (cancelled) return;

        if (requestError.response?.status === 404) {
          setNotFound(true);
        } else {
          setError(
            getApiError(requestError, "Could not load this product.")
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (!product) return undefined;

    let cancelled = false;

    getRelatedProducts(product.id, 4)
      .then((items) => {
        if (!cancelled) setRelated(items);
      })
      .catch(() => {
        if (!cancelled) setRelated([]);
      });

    return () => {
      cancelled = true;
    };
  }, [product]);

  const colors = useMemo(() => {
    if (!product) return [];
    return [...new Set(product.variants.map((variant) => variant.color))];
  }, [product]);

  const sizes = useMemo(() => {
    if (!product) return [];
    return sortSizes([
      ...new Set(product.variants.map((variant) => variant.size)),
    ]);
  }, [product]);

  const findVariant = (color, size) =>
    product?.variants.find(
      (variant) => variant.color === color && variant.size === size
    ) ?? null;

  const selectedVariant = findVariant(selectedColor, selectedSize);
  const wished = product ? isWishlisted(product.id) : false;
  const cartItem =
    product && selectedVariant
      ? cart.find(
          (item) =>
            item.key === getCartKey(product.id, selectedVariant.id)
        )
      : null;
  const atMaxStock = Boolean(
    selectedVariant &&
      cartItem &&
      cartItem.quantity >= selectedVariant.stock
  );

  const images = product
    ? product.images.length > 0
      ? product.images.map((image) => image.url)
      : product.image
        ? [product.image]
        : []
    : [];

  const handleColorChange = (color) => {
    setSelectedColor(color);
    setMessage("");

    if (!findVariant(color, selectedSize)) {
      const fallback =
        product.variants.find(
          (variant) => variant.color === color && variant.stock > 0
        ) ??
        product.variants.find((variant) => variant.color === color);

      if (fallback) {
        setSelectedSize(fallback.size);
      }
    }
  };

  const handleAddToCart = async () => {
    if (
      !product ||
      !selectedVariant ||
      selectedVariant.stock === 0 ||
      atMaxStock
    ) {
      return;
    }

    setAdding(true);
    setMessage("");
    setMessageError(false);

    try {
      const added = await addToCart(product, selectedVariant);

      if (added) {
        setMessage("Added to cart.");
        setMessageError(false);
        openCart();
      } else {
        setMessage(
          "Maximum available stock is already in your cart."
        );
        setMessageError(true);
      }
    } catch (error) {
      setMessage(error.message || "Could not add to cart.");
      setMessageError(true);
    } finally {
      setAdding(false);
    }
  };

  const handleWishlist = async () => {
    if (!product) return;

    if (!user) {
      navigate("/login", { state: { from: location.pathname } });
      return;
    }

    setMessage("");
    setMessageError(false);

    try {
      await toggleWishlist(product);
    } catch (error) {
      setMessage(error.message || "Could not update your wishlist.");
      setMessageError(true);
    }
  };

  if (loading) {
    return (
      <p className="min-h-screen px-6 pt-20 text-center text-gray-400">
        Loading product...
      </p>
    );
  }

  if (notFound) {
    return (
      <div className="min-h-screen px-6 pt-20 text-center">
        <h1 className="text-4xl font-bold">Product not found</h1>
        <p className="text-gray-400 mt-4">
          It may have been removed or is no longer available.
        </p>
        <Link
          to="/shop"
          className="inline-block mt-8 bg-cyan-400 text-black px-6 py-2 rounded-lg"
        >
          Back to shop
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen px-6 pt-20 text-center">
        <p className="text-red-400">{error}</p>
        <Link
          to="/shop"
          className="inline-block mt-6 text-cyan-400 hover:text-cyan-300"
        >
          Back to shop
        </Link>
      </div>
    );
  }

  if (!product) return null;

  const hasVariants = product.variants.length > 0;
  const stockLabel = !hasVariants
    ? "No sizes available"
    : !selectedVariant
      ? "Select a size"
      : selectedVariant.stock === 0
        ? "Out of stock"
        : selectedVariant.stock <= 5
          ? `Only ${selectedVariant.stock} left`
          : "In stock";

  const buttonDisabled =
    !hasVariants ||
    !selectedVariant ||
    selectedVariant.stock === 0 ||
    atMaxStock;

  const buttonLabel = !hasVariants
    ? "Unavailable"
    : !selectedVariant
      ? "Select a size"
      : selectedVariant.stock === 0
        ? "Out of stock"
        : atMaxStock
          ? "Maximum in cart"
          : "Add to cart";

  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-8">
      <div className="max-w-6xl mx-auto">
        <Link
          to="/shop"
          className="text-sm text-gray-400 hover:text-cyan-400"
        >
          ← Back to shop
        </Link>

        <div className="grid lg:grid-cols-2 gap-10 mt-6">
          {/* GALLERY */}
          <div>
            <div className="bg-[#020617] border border-gray-800 rounded-2xl overflow-hidden">
              {images.length > 0 ? (
                <img
                  src={imageUrl(images[selectedImage])}
                  alt={product.name}
                  className="w-full h-[420px] object-cover"
                />
              ) : (
                <div className="w-full h-[420px] bg-gray-900 flex items-center justify-center text-gray-500">
                  No image
                </div>
              )}
            </div>

            {images.length > 1 && (
              <div className="flex gap-3 mt-4">
                {images.map((url, index) => (
                  <button
                    key={`${url}-${index}`}
                    type="button"
                    onClick={() => setSelectedImage(index)}
                    aria-label={`View image ${index + 1}`}
                    className={`w-20 h-20 rounded-lg overflow-hidden border-2 ${
                      selectedImage === index
                        ? "border-cyan-400"
                        : "border-gray-800"
                    }`}
                  >
                    <img
                      src={imageUrl(url)}
                      alt={`${product.name} thumbnail ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* DETAILS */}
          <div>
            {product.category && (
              <p className="text-sm uppercase tracking-wide text-cyan-400">
                {product.category.name}
              </p>
            )}

            <h1 className="text-4xl font-bold mt-2">{product.name}</h1>

            <p className="text-2xl text-cyan-400 mt-4">
              LKR {product.price}
            </p>

            <p className="text-gray-400 mt-6 leading-7 whitespace-pre-line">
              {product.description}
            </p>

            <div className="mt-8 space-y-5">
              {hasVariants ? (
                <>
                  {/* COLOR */}
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-gray-300">
                        Color
                      </span>
                      <span className="text-xs text-gray-500">
                        {selectedColor || "—"}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-2 mt-2">
                      {colors.map((color) => {
                        const available = product.variants.some(
                          (variant) =>
                            variant.color === color && variant.stock > 0
                        );

                        return (
                          <button
                            key={color}
                            type="button"
                            onClick={() => handleColorChange(color)}
                            aria-label={`Select color ${color}`}
                            className={`px-4 py-2 rounded-lg border text-sm transition ${
                              selectedColor === color
                                ? "border-cyan-400 bg-cyan-400 text-black"
                                : available
                                  ? "border-gray-700 text-gray-200 hover:border-cyan-400"
                                  : "border-gray-800 text-gray-600"
                            }`}
                          >
                            {color}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* SIZE */}
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-gray-300">
                        Size
                      </span>
                      <span className="text-xs text-gray-500">
                        {stockLabel}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-2 mt-2">
                      {sizes.map((size) => {
                        const variant = findVariant(selectedColor, size);
                        const soldOut = !variant || variant.stock === 0;

                        return (
                          <button
                            key={size}
                            type="button"
                            onClick={() => {
                              setSelectedSize(size);
                              setMessage("");
                            }}
                            disabled={soldOut}
                            aria-label={`Select size ${size}`}
                            className={`min-w-[48px] px-3 py-2 rounded-lg border text-sm transition ${
                              selectedSize === size
                                ? "border-cyan-400 bg-cyan-400 text-black"
                                : soldOut
                                  ? "border-gray-800 text-gray-600 line-through"
                                  : "border-gray-700 text-gray-200 hover:border-cyan-400"
                            }`}
                          >
                            {size}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-red-400">
                  This product has no available sizes.
                </p>
              )}
            </div>

            {selectedVariant && (
              <p className="text-xs text-gray-500 mt-4">
                SKU: {selectedVariant.sku}
              </p>
            )}

            {message && (
              <p
                className={`text-sm mt-4 ${
                  messageError ? "text-red-400" : "text-green-400"
                }`}
              >
                {message}
              </p>
            )}

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={buttonDisabled || adding}
                className="flex-1 bg-cyan-400 text-black py-3 rounded-lg font-semibold hover:bg-cyan-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {adding ? "Adding..." : buttonLabel}
              </button>

              <button
                type="button"
                onClick={handleWishlist}
                aria-label={
                  wished
                    ? "Remove this product from your wishlist"
                    : "Add this product to your wishlist"
                }
                aria-pressed={wished}
                className={`px-4 rounded-lg border text-xl transition ${
                  wished
                    ? "border-red-500/60 bg-red-500/10 text-red-400"
                    : "border-gray-700 text-gray-300 hover:border-red-400 hover:text-red-400"
                }`}
              >
                <FiHeart fill={wished ? "currentColor" : "none"} />
              </button>
            </div>

            <p className="text-xs text-gray-500 mt-4">
              Secure checkout and delivery options will be available soon.
            </p>
          </div>
        </div>

        <div className="mt-14">
          <ProductReviews productId={product.id} />
        </div>

        {related.length > 0 && (
          <section
            aria-labelledby="related-heading"
            className="mt-14"
          >
            <h2
              id="related-heading"
              className="text-2xl font-bold"
            >
              You may also like
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-6">
              {related.map((item) => (
                <ProductCard key={item.id} product={item} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function ProductDetailRoute() {
  const { slug } = useParams();
  return <ProductDetail key={slug} slug={slug} />;
}

export default ProductDetailRoute;
