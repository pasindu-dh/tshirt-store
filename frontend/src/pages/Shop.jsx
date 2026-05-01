import { useEffect, useState } from "react";
import axios from "axios";
import InfiniteScroll from "react-infinite-scroll-component";
import { Routes, Route, useNavigate } from "react-router-dom";

function Shop() {
  const [products, setProducts] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchProducts = async () => {
    try {
      const res = await axios.get(
        `http://127.0.0.1:8005/products?page=${page}`
      );

      const newProducts = res.data;

      setProducts((prev) => [...prev, ...newProducts]);

      if (newProducts.length === 0) {
        setHasMore(false);
      }

    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [page]);

  const fetchMoreData = () => {
    setPage((prev) => prev + 1);
  };

  // ✅ THIS WAS MISSING
  return (
    <div className="min-h-screen px-10 pt-18 pb-20">

      {/* 🔥 GAP FIX HERE */}
      <h1 className="text-4xl font-bold mt-10 mb-10 text-center scroll-mt-24">
        Shop
      </h1>

      <InfiniteScroll
        dataLength={products.length}
        next={fetchMoreData}
        hasMore={hasMore}
        loader={<h4 className="text-center">Loading...</h4>}
        endMessage={<p className="text-center">No more products</p>}
      >
        <div className="grid md:grid-cols-3 gap-8">
          {products.map((p) => (
            <div
              key={p.id}
              className="bg-[#020617] border border-gray-800 rounded-xl p-4"
            >
              <img
                src={p.image}
                className="h-60 w-full object-cover rounded"
                alt={p.name}
              />
              <h3 className="mt-3 text-lg">{p.name}</h3>
              <p className="text-gray-400">LKR {p.price}</p>
            </div>
          ))}
        </div>
      </InfiniteScroll>
    </div>
  );
}

export default Shop;