import { useEffect, useState } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import { getProducts } from "../api/products";
import ProductCard from "../components/ProductCard";

const PAGE_SIZE = 6;

function Shop({ search }) {
  const [products, setProducts] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getProducts({ page, limit: PAGE_SIZE })
      .then((data) => {
        if (cancelled) return;

        setProducts((current) => [...current, ...data]);

        if (data.length < PAGE_SIZE) {
          setHasMore(false);
        }

        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;

        setError("Could not load products. Is the backend running?");
        setHasMore(false);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page]);

  const filteredProducts = products.filter((product) =>
    product.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen px-10 pt-10 pb-20">
      <h1 className="text-4xl font-bold mb-10 text-center">Shop</h1>

      {loading ? (
        <p className="text-center text-gray-400">Loading products...</p>
      ) : error ? (
        <p className="text-center text-red-400">{error}</p>
      ) : (
        <InfiniteScroll
          dataLength={products.length}
          next={() => setPage((current) => current + 1)}
          hasMore={hasMore}
          loader={<h4 className="text-center mt-6 text-gray-400">Loading...</h4>}
          endMessage={
            products.length > 0 ? (
              <p className="text-center mt-10 text-gray-400">
                You&apos;ve seen all products
              </p>
            ) : null
          }
        >
          {filteredProducts.length === 0 ? (
            <p className="text-center text-gray-400">
              No products match &quot;{search}&quot; 😢
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {filteredProducts.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </InfiniteScroll>
      )}
    </div>
  );
}

export default Shop;
