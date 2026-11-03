import { NavLink, Outlet } from "react-router-dom";

const tabClass = ({ isActive }) =>
  `px-4 py-2 rounded-lg text-sm font-semibold transition ${
    isActive
      ? "bg-cyan-400 text-black"
      : "text-gray-300 hover:text-cyan-400"
  }`;

function AdminLayout() {
  return (
    <div className="min-h-screen px-6 md:px-10 pb-20 pt-8">
      <h1 className="text-4xl font-bold text-center">Admin</h1>
      <p className="text-center text-gray-400 mt-2">
        Manage products, categories, and stock
      </p>

      <nav className="flex flex-wrap justify-center gap-3 mt-8">
        <NavLink to="/admin" end className={tabClass}>
          Dashboard
        </NavLink>

        <NavLink to="/admin/orders" className={tabClass}>
          Orders
        </NavLink>

        <NavLink to="/admin/products" className={tabClass}>
          Products
        </NavLink>

        <NavLink to="/admin/categories" className={tabClass}>
          Categories
        </NavLink>

        <NavLink to="/admin/coupons" className={tabClass}>
          Coupons
        </NavLink>

        <NavLink
          to="/shop"
          className="px-4 py-2 rounded-lg text-sm font-semibold border border-gray-700 text-gray-300 hover:border-cyan-400 hover:text-cyan-400 transition"
        >
          View store
        </NavLink>
      </nav>

      <div className="max-w-6xl mx-auto mt-10">
        <Outlet />
      </div>
    </div>
  );
}

export default AdminLayout;
