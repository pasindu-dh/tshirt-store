import { useState } from "react";
import {
  FiHeart,
  FiLogOut,
  FiMenu,
  FiPackage,
  FiSearch,
  FiShoppingBag,
  FiX,
} from "react-icons/fi";
import { useLocation, useNavigate } from "react-router-dom";
import useAuth from "../hooks/useAuth";
import useCart from "../hooks/useCart";
import useWishlist from "../hooks/useWishlist";

const primaryLinks = [
  { label: "Home", path: "/" },
  { label: "Shop", path: "/shop" },
  { label: "About", path: "/about" },
  { label: "Contact", path: "/contact" },
];

function Navbar({ search, setSearch }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { cartCount, openCart } = useCart();
  const { user, isAdmin, logout } = useAuth();
  const { wishlistCount } = useWishlist();
  const [mobileOpen, setMobileOpen] = useState(false);

  const closeMobile = () => setMobileOpen(false);

  const goHome = () => {
    closeMobile();

    if (location.pathname === "/") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      navigate("/");
    }
  };

  const navigateTo = (path) => {
    closeMobile();
    navigate(path);
  };

  const handleSearchChange = (event) => {
    setSearch(event.target.value);

    // Search results live on the shop page, so go there as soon as the user types.
    if (location.pathname !== "/shop") {
      navigate("/shop");
    }
  };

  const handleLogout = () => {
    closeMobile();
    logout();
  };

  return (
    <nav className="fixed top-0 left-0 w-full h-20 z-50 backdrop-blur-md bg-[#020617]/80 border-b border-gray-800">
      <div className="flex justify-between items-center h-full px-4 sm:px-6 md:px-10">
        {/* LOGO */}
        <h1
          onClick={goHome}
          className="text-2xl sm:text-3xl md:text-4xl font-bold cursor-pointer hover:scale-105 transition"
        >
          <span className="text-cyan-400">FU</span>
          <span className="text-white">R</span>
          <span className="text-cyan-400">ZY</span>
        </h1>

        {/* MENU */}
        <ul className="hidden md:flex gap-8 lg:gap-10 text-gray-200">
          {primaryLinks.map((link) => (
            <li key={link.path}>
              <button
                type="button"
                onClick={() => {
                  if (link.path === "/") {
                    goHome();
                  } else {
                    navigate(link.path);
                  }
                }}
                className="cursor-pointer hover:text-cyan-400"
              >
                {link.label}
              </button>
            </li>
          ))}

          {isAdmin && (
            <li>
              <button
                type="button"
                onClick={() => navigate("/admin")}
                className="cursor-pointer text-cyan-400 hover:text-cyan-300"
              >
                Admin
              </button>
            </li>
          )}
        </ul>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-3 md:gap-5">
          {/* SEARCH */}
          <div className="hidden lg:flex items-center bg-[#111827] px-4 py-2 rounded-full w-56">
            <FiSearch className="text-gray-400 mr-2" />
            <input
              type="text"
              value={search}
              onChange={handleSearchChange}
              placeholder="Search..."
              aria-label="Search products"
              className="bg-transparent outline-none w-full text-sm text-white"
            />
          </div>

          {/* CART */}
          <button
            type="button"
            onClick={() => {
              closeMobile();
              openCart();
            }}
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
              <button
                type="button"
                onClick={() => navigateTo("/orders")}
                aria-label="My orders"
                className="text-xl text-gray-300 hover:text-cyan-400 transition"
              >
                <FiPackage />
              </button>

              <button
                type="button"
                onClick={() => navigateTo("/wishlist")}
                aria-label="My wishlist"
                className="relative text-xl text-gray-300 hover:text-red-400 transition"
              >
                <FiHeart />
                {wishlistCount > 0 && (
                  <span className="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                    {wishlistCount}
                  </span>
                )}
              </button>

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
              onClick={() => navigateTo("/login")}
              className="text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition"
            >
              Login
            </button>
          )}

          {/* MOBILE MENU TOGGLE */}
          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            className="lg:hidden text-xl text-gray-300 hover:text-cyan-400 transition"
          >
            {mobileOpen ? <FiX /> : <FiMenu />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div
          id="mobile-nav"
          className="lg:hidden fixed top-20 left-0 w-full bg-[#020617] border-b border-gray-800 px-4 py-4 shadow-xl"
        >
          <div className="flex items-center bg-[#111827] px-4 py-2 rounded-full mb-4">
            <FiSearch className="text-gray-400 mr-2" />
            <input
              type="text"
              value={search}
              onChange={handleSearchChange}
              placeholder="Search products..."
              aria-label="Search products"
              className="bg-transparent outline-none w-full text-sm text-white"
            />
          </div>

          <div className="flex flex-col gap-1 text-gray-200">
            {primaryLinks.map((link) => (
              <button
                key={link.path}
                type="button"
                onClick={() => {
                  closeMobile();
                  if (link.path === "/") {
                    goHome();
                  } else {
                    navigate(link.path);
                  }
                }}
                className="text-left px-3 py-2 rounded-lg hover:bg-white/5 hover:text-cyan-400"
              >
                {link.label}
              </button>
            ))}

            {user && (
              <button
                type="button"
                onClick={() => navigateTo("/orders")}
                className="text-left px-3 py-2 rounded-lg hover:bg-white/5 hover:text-cyan-400"
              >
                My orders
              </button>
            )}

            {user && (
              <button
                type="button"
                onClick={() => navigateTo("/wishlist")}
                className="text-left px-3 py-2 rounded-lg hover:bg-white/5 hover:text-red-400"
              >
                My wishlist
              </button>
            )}

            {isAdmin && (
              <button
                type="button"
                onClick={() => navigateTo("/admin")}
                className="text-left px-3 py-2 rounded-lg text-cyan-400 hover:bg-white/5 hover:text-cyan-300"
              >
                Admin panel
              </button>
            )}

            {!user && (
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => navigateTo("/login")}
                  className="flex-1 rounded-lg border border-cyan-400 px-3 py-2 font-semibold text-cyan-400 hover:bg-cyan-400 hover:text-black transition"
                >
                  Login
                </button>
                <button
                  type="button"
                  onClick={() => navigateTo("/register")}
                  className="flex-1 rounded-lg bg-cyan-400 px-3 py-2 font-semibold text-black hover:bg-cyan-300 transition"
                >
                  Create account
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}

export default Navbar;
