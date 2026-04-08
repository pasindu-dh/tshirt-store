import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    console.log("Fetching products...");

    axios.get("http://127.0.0.1:8000/products")
      .then(res => {
        console.log("DATA:", res.data); // 👈 IMPORTANT
        setProducts(res.data);
      })
      .catch(err => {
        console.error("ERROR:", err); // 👈 IMPORTANT
      });
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h1>T-Shirt Store</h1>

      {products.length === 0 ? (
        <p>Loading...</p>
      ) : (
        products.map(p => (
          <div key={p.id}>
            <h3>{p.name}</h3>
            <p>LKR {p.price}</p>
          </div>
        ))
      )}
    </div>
  );
}

export default App;