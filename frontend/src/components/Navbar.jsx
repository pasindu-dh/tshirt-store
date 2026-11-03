import { FiLogOut, FiSearch, FiShoppingBag } from "react-icons/fi";
import { useLocation, useNavigate } from "react-router-dom";
import useAuth from "../hooks/useAuth";
import useCart from "../hooks/useCart";

function Navbar({ search, setSearch }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { cartCount, openCart } = useCart();
  const { user, isAdmin, logout } = useAuth();

  const goHome = () => {
    if (location.pathname === "/") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      navigate("/");
    }
  };

  const handleSearchChange = (event) => {
    setSearch(event.target.value);

    // Search results live on the shop page, so go there as soon as the user types.
    if (location.pathname !== "/shop") {
      navigate("/shop");
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <nav className="fixed top-0 left-0 w-full h-20 z-50 backdrop-blur-md bg-[#020617]/80 border-b border-gray-800">
      <div className="flex justify-between items-center px-10 py-5">
        {/* LOGO */}
        <h1
          onClick={goHome}
          className="text-4xl font-bold cursor-pointer hover:scale-105 transition"
        >
          <span className="text-cyan-400">FU</span>
          <span className="text-white">R</span>
          <span className="text-cyan-400">ZY</span>
        </h1>

        {/* MENU */}
        <ul className="hidden md:flex gap-10 text-gray-200">
          <li
            onClick={goHome}
            className="cursor-pointer hover:text-cyan-400"
          >
            Home
          </li>

          <li
            onClick={() => navigate("/shop")}
            className="cursor-pointer hover:text-cyan-400"
          >
            Shop
          </li>

          <li
            onClick={() => navigate("/about")}
            className="cursor-pointer hover:text-cyan-400"
          >
            About
          </li>

          <li
            onClick={() => navigate("/contact")}
            className="cursor-pointer hover:text-cyan-400"
          >
            Contact
          </li>

          {isAdmin && (
            <li
              onClick={() => navigate("/admin")}
              className="cursor-pointer text-cyan-400 hover:text-cyan-300"
            >
              Admin
            </li>
          )}
        </ul>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-5">
          {/* SEARCH */}
          <div className="hidden lg:flex items-center bg-[#111827] px-4 py-2 rounded-full w-56">
            <FiSearch className="text-gray-400 mr-2" />
            <input
              type="text"
              value={search}
              onChange={handleSearchChange}
              placeholder="Search..."
              className="bg-transparent outline-none w-full text-sm text-white"
            />
          </div>

          {/* CART */}
          <button
            type="button"
            onClick={openCart}
            aria-label="Open cart"
            className="relative cursor-pointer"
          >
            <FiShoppingBag className="text-xl hover:text-cyan-400" />
            {cartCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-cyan-400 text-black text-xs px-2 py-0.5 rounded-full">
                {cartCount}
              </span>
            )}
          </button>

          {/* ACCOUNT */}
          {user ? (
            <div className="flex items-center gap-3">
              <span className="hidden xl:block max-w-[140px] truncate text-sm text-gray-300">
                {user.name}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                aria-label="Log out"
                className="text-xl text-gray-300 hover:text-cyan-400 transition"
              >
                <FiLogOut />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition"
            >
              Login
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
