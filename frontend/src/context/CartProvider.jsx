import { useEffect, useState } from "react";
import { getCartKey, normalizeCartItem } from "../utils/cart";
import CartContext from "./CartContext";

const STORAGE_KEY = "cart";

function readStoredCart() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    const parsed = saved ? JSON.parse(saved) : [];
    return Array.isArray(parsed) ? parsed.map(normalizeCartItem) : [];
  } catch {
    return [];
  }
}

export default function CartProvider({ children }) {
  const [cart, setCart] = useState(readStoredCart);
  const [isCartOpen, setIsCartOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    } catch {
      // Storage can be unavailable (e.g. private mode); the cart still works in memory.
    }
  }, [cart]);

  const addToCart = (product, variant = null) => {
    if (variant && variant.stock <= 0) {
      return false;
    }

    const variantId = variant?.id ?? null;
    const key = getCartKey(product.id, variantId);
    const maxStock = variant?.stock ?? Infinity;
    const existing = cart.find((item) => item.key === key);

    if (existing && existing.quantity >= (existing.stock ?? maxStock)) {
      return false;
    }

    setCart((current) => {
      const currentItem = current.find((item) => item.key === key);

      if (currentItem) {
        const stock = currentItem.stock ?? maxStock;

        if (currentItem.quantity >= stock) {
          return current;
        }

        return current.map((item) =>
          item.key === key
            ? {
                ...item,
                quantity: item.quantity + 1,
                stock: variant?.stock ?? item.stock,
              }
            : item
        );
      }

      return [
        ...current,
        {
          key,
          productId: product.id,
          variantId,
          id: product.id,
          name: product.name,
          price: product.price,
          image: product.image,
          size: variant?.size ?? null,
          color: variant?.color ?? null,
          sku: variant?.sku ?? null,
          stock: variant?.stock ?? null,
          quantity: 1,
        },
      ];
    });

    return true;
  };

  const increaseQty = (key) => {
    setCart((current) =>
      current.map((item) => {
        if (item.key !== key) return item;

        const maxStock = item.stock ?? Infinity;

        if (item.quantity >= maxStock) {
          return item;
        }

        return { ...item, quantity: item.quantity + 1 };
      })
    );
  };

  const decreaseQty = (key) => {
    setCart((current) =>
      current
        .map((item) =>
          item.key === key
            ? { ...item, quantity: item.quantity - 1 }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const removeItem = (key) => {
    setCart((current) => current.filter((item) => item.key !== key));
  };

  const clearCart = () => setCart([]);

  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);
  const cartTotal = cart.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  const value = {
    cart,
    addToCart,
    increaseQty,
    decreaseQty,
    removeItem,
    clearCart,
    cartCount,
    cartTotal,
    isCartOpen,
    openCart: () => setIsCartOpen(true),
    closeCart: () => setIsCartOpen(false),
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
