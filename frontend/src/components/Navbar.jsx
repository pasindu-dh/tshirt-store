import { FiSearch, FiShoppingBag } from "react-icons/fi";
import { useNavigate, useLocation } from "react-router-dom";

function Navbar({ setSearch, cartCount, openCart }) {

  const navigate = useNavigate();
  const location = useLocation();

  const handleScroll = (id) => {
    if (location.pathname !== "/") {
      // If not on home → go home first
      navigate("/");
      
      // Wait for page to load, then scroll
      setTimeout(() => {
        const section = document.getElementById(id);
        section?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } else {
      // Already on home → just scroll
      const section = document.getElementById(id);
      section?.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <nav className="fixed top-0 left-0 w-full z-50 backdrop-blur-md bg-[#020617]/80 border-b border-gray-800">
      
      <div className="flex justify-between items-center px-10 py-5">

        {/* LOGO */}
        <h1
          onClick={() => handleScroll("home")}
          className="text-4xl font-bold cursor-pointer hover:scale-105 transition"
        >
          <span className="text-cyan-400">FU</span>
          <span className="text-white">R</span>
          <span className="text-cyan-400">ZY</span>
        </h1>

        {/* MENU */}
        <ul className="hidden md:flex gap-10 text-gray-200">

          <li onClick={() => handleScroll("home")} className="cursor-pointer hover:text-cyan-400">
            Home
          </li>

          <li onClick={() => handleScroll("shop")} className="cursor-pointer hover:text-cyan-400">
            Shop
          </li>

          <li onClick={() => navigate("/about")} className="cursor-pointer hover:text-cyan-400">
            About
          </li>

          <li onClick={() => navigate("/contact")} className="cursor-pointer hover:text-cyan-400">
            Contact
          </li>

        </ul>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-5">

          {/* SEARCH */}
          <div className="flex items-center bg-[#111827] px-4 py-2 rounded-full w-56">
            <FiSearch className="text-gray-400 mr-2" />
            <input
              type="text"
              placeholder="Search..."
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent outline-none w-full text-sm text-white"
            />
          </div>

          {/* CART */}
          <div onClick={openCart} className="relative cursor-pointer">
            <FiShoppingBag className="text-xl hover:text-cyan-400" />
            {cartCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-cyan-400 text-black text-xs px-2 py-0.5 rounded-full">
                {cartCount}
              </span>
            )}
          </div>

        </div>
      </div>
    </nav>
  );
}

export default Navbar;