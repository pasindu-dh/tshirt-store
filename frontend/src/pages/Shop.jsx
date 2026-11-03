import { useCallback, useEffect, useRef, useState } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import { getCategories } from "../api/categories";
import { getProducts } from "../api/products";
import ProductCard from "../components/ProductCard";
import { getApiError } from "../utils/errors";

const PAGE_SIZE = 6;
const SORT_OPTIONS = [
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "name", label: "Name: A–Z" },
];

function Shop({ search, setSearch }) {
  const initialSearch = search.trim();

  const [products, setProducts] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [appliedSearch, setAppliedSearch] = useState(initialSearch);
  const appliedSearchRef = useRef(initialSearch);
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("newest");
  const [categories, setCategories] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  const resetResults = useCallback(() => {
    setPage(1);
    setProducts([]);
    setHasMore(true);
    setTotal(0);
    setError("");
    setLoading(true);
  }, []);

  useEffect(() => {
    const trimmed = search.trim();
    const timeout = setTimeout(() => {
      if (appliedSearchRef.current === trimmed) return;

      appliedSearchRef.current = trimmed;
      setAppliedSearch(trimmed);
      resetResults();
    }, 300);

    return () => clearTimeout(timeout);
  }, [search, resetResults]);

  useEffect(() => {
    let cancelled = false;

    getProducts({
      page,
      limit: PAGE_SIZE,
      search: appliedSearch || undefined,
      category: category || undefined,
      sort,
    })
      .then((result) => {
        if (cancelled) return;

        setProducts((current) =>
          page === 1 ? result.products : [...current, ...result.products]
        );
        setTotal(result.total);
        setHasMore(page * PAGE_SIZE < result.total);
        setError("");
      })
      .catch((requestError) => {
        if (cancelled) return;

        setError(
          getApiError(requestError, "Could not load products.")
        );
        setHasMore(false);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, appliedSearch, category, sort, refreshKey]);

  const handleCategoryChange = (event) => {
    setCategory(event.target.value);
    resetResults();
  };

  const handleSortChange = (event) => {
    setSort(event.target.value);
    resetResults();
  };

  const clearFilters = () => {
    setSearch("");
    appliedSearchRef.current = "";
    setAppliedSearch("");
    setCategory("");
    setSort("newest");
    resetResults();
  };

  const hasFilters = Boolean(
    search.trim() || category || sort !== "newest"
  );
  const showInitialLoading = loading && products.length === 0;

  return (
    <div className="min-h-screen px-6 md:px-10 pt-10 pb-20">
      <div className="max-w-7xl mx-auto">
        <div className="text-center">
          <h1 className="text-4xl font-bold">Shop</h1>
          <p className="text-gray-400 mt-2">
            Browse the full FURZY collection.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4 mt-8">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-end flex-1">
            <label className="flex flex-col gap-1 text-sm text-gray-400 flex-1 min-w-[200px]">
              Search
              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search products..."
                aria-label="Search products"
                className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm text-gray-400">
              Category
              <select
                value={category}
                onChange={handleCategoryChange}
                aria-label="Filter by category"
                className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
              >
                <option value="">All categories</option>
                {categories.map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm text-gray-400">
              Sort
              <select
                value={sort}
                onChange={handleSortChange}
                aria-label="Sort products"
                className="p-3 rounded-lg bg-[#020617] border border-gray-700 outline-none focus:border-cyan-400"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex items-center gap-4">
            <p className="text-sm text-gray-400">
              {total} product{total === 1 ? "" : "s"}
            </p>

            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-sm text-cyan-400 hover:text-cyan-300"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>

        {error ? (
          <div className="mt-10 text-center">
            <p className="text-red-400">{error}</p>
            <button
              type="button"
              onClick={() => {
                resetResults();
                setRefreshKey((current) => current + 1);
              }}
              className="mt-4 px-5 py-2 rounded-lg border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400"
            >
              Try again
            </button>
          </div>
        ) : showInitialLoading ? (
          <p className="mt-10 text-center text-gray-400">
            Loading products...
          </p>
        ) : products.length === 0 ? (
          <div className="mt-10 text-center">
            <p className="text-gray-400">
              No products found
              {appliedSearch ? ` for "${appliedSearch}"` : ""}.
            </p>

            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="mt-4 text-sm text-cyan-400 hover:text-cyan-300"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <InfiniteScroll
            dataLength={products.length}
            next={() => {
              setLoading(true);
              setPage((current) => current + 1);
            }}
            hasMore={hasMore}
            loader={
              <h4 className="text-center mt-6 text-gray-400">
                Loading...
              </h4>
            }
            endMessage={
              <p className="text-center mt-10 text-gray-400">
                You&apos;ve seen all products
              </p>
            }
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 mt-8">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </InfiniteScroll>
        )}
      </div>
    </div>
  );
}

export default Shop;
