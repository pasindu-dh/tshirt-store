import { useCallback, useEffect, useRef, useState } from "react";
import {
  addWishlistItem,
  getWishlist,
  removeWishlistItem,
} from "../api/wishlist";
import useAuth from "../hooks/useAuth";
import { getApiError } from "../utils/errors";
import WishlistContext from "./WishlistContext";

export default function WishlistProvider({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const syncedUserIdRef = useRef(null);

  const loadWishlist = useCallback(async () => {
    if (!user) {
      setItems([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await getWishlist();
      setItems(data);
    } catch (requestError) {
      setError(
        getApiError(requestError, "Could not load your wishlist.")
      );
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;

    const userId = user?.id ?? null;

    if (syncedUserIdRef.current === userId) return;

    syncedUserIdRef.current = userId;

    if (!userId) {
      setItems([]);
      setError("");
      setLoading(false);
      return;
    }

    loadWishlist();
  }, [user, authLoading, loadWishlist]);

  const isWishlisted = useCallback(
    (productId) =>
      items.some((item) => item.product_id === productId),
    [items]
  );

  const toggleWishlist = useCallback(
    async (product) => {
      if (!user) {
        return { requiresAuth: true, wishlisted: false };
      }

      const existing = items.find(
        (item) => item.product_id === product.id
      );
      setError("");

      try {
        if (existing) {
          await removeWishlistItem(product.id);
          setItems((current) =>
            current.filter(
              (item) => item.product_id !== product.id
            )
          );
          return { requiresAuth: false, wishlisted: false };
        }

        const created = await addWishlistItem(product.id);
        setItems((current) => {
          if (
            current.some(
              (item) => item.product_id === product.id
            )
          ) {
            return current;
          }

          return [created, ...current];
        });
        return { requiresAuth: false, wishlisted: true };
      } catch (requestError) {
        const message = getApiError(
          requestError,
          "Could not update your wishlist."
        );
        setError(message);
        throw new Error(message);
      }
    },
    [items, user]
  );

  const value = {
    items,
    loading,
    error,
    wishlistCount: items.length,
    isWishlisted,
    toggleWishlist,
    reloadWishlist: loadWishlist,
  };

  return (
    <WishlistContext.Provider value={value}>
      {children}
    </WishlistContext.Provider>
  );
}
