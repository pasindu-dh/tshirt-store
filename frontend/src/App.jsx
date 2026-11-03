import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import Cart from "./components/Cart";
import Navbar from "./components/Navbar";
import ParticleBackground from "./components/ParticleBackground";
import About from "./pages/About";
import Checkout from "./pages/Checkout";
import Contact from "./pages/Contact";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";
import Shop from "./pages/Shop";

function App() {
  const [search, setSearch] = useState("");

  return (
    <>
      <ParticleBackground />

      <div className="relative z-10 bg-black text-white min-h-screen pt-20">
        <Navbar search={search} setSearch={setSearch} />
        <Cart />

        <Routes>
          <Route path="/" element={<Home search={search} />} />
          <Route path="/shop" element={<Shop search={search} />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
    </>
  );
}

export default App;
