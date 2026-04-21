import { useEffect, useState } from "react";
import axios from "axios";

function Shop() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    axios.get("http://127.0.0.1:8000/products")
      .then(res => setProducts(res.data));
  }, []);

  return (
    <div className="pt-24 px-10">
      <h1 className="text-3xl font-bold mb-6">Shop</h1>

      <div className="grid md:grid-cols-3 gap-8">
        {products.map((p) => (
          <div key={p.id} className="bg-[#020617] border border-gray-800 rounded-xl p-4">
            <img src={p.image} className="h-60 w-full object-cover rounded"/>
            <h3 className="mt-3 text-lg">{p.name}</h3>
            <p className="text-gray-400">LKR {p.price}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Shop;