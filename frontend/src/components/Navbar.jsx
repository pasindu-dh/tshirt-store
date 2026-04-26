import { FiSearch, FiShoppingBag } from "react-icons/fi";

function Navbar({ setSearch, cartCount, openCart }) {

  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    section?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <nav className="fixed top-0 left-0 w-full z-50 backdrop-blur-md bg-[#020617]/80 border-b border-gray-800">
      
      <div className="flex justify-between items-center px-10 py-4">

        {/* LOGO */}
        <h1
          onClick={() => scrollToSection("home")}
          className="text-2xl font-bold cursor-pointer hover:scale-105 transition"
        >
          <span className="text-cyan-400">FU</span>
          <span className="text-white">R</span>
          <span className="text-cyan-400">ZY</span>
        </h1>

        {/* MENU */}
        <ul className="hidden md:flex gap-8 text-gray-300">
          <li onClick={() => scrollToSection("home")} className="cursor-pointer hover:text-cyan-400 transition">Home</li>
          <li onClick={() => scrollToSection("shop")} className="cursor-pointer hover:text-cyan-400 transition">Shop</li>
          <li onClick={() => scrollToSection("about")} className="cursor-pointer hover:text-cyan-400 transition">About</li>
          <li onClick={() => scrollToSection("contact")} className="cursor-pointer hover:text-cyan-400 transition">Contact</li>
        </ul>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-5">

          {/* SEARCH BAR */}
          <div className="flex items-center bg-[#111827] px-4 py-2 rounded-full w-56">
            <FiSearch className="text-gray-400 mr-2" />
            <input
              type="text"
              placeholder="Search..."
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent outline-none w-full text-sm text-white placeholder-gray-400"
            />
          </div>

          {/* CART ICON */}
          <div
            onClick={openCart}
            className="relative cursor-pointer"
          >
            <FiShoppingBag className="text-xl hover:text-cyan-400 transition" />

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