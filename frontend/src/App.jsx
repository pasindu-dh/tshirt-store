import { lazy, Suspense, useState } from "react";
import { Route, Routes } from "react-router-dom";
import Cart from "./components/Cart";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

const ParticleBackground = lazy(
  () => import("./components/ParticleBackground")
);
const About = lazy(() => import("./pages/About"));
const Checkout = lazy(() => import("./pages/Checkout"));
const Contact = lazy(() => import("./pages/Contact"));
const Forbidden = lazy(() => import("./pages/Forbidden"));
const Home = lazy(() => import("./pages/Home"));
const Login = lazy(() => import("./pages/Login"));
const NotFound = lazy(() => import("./pages/NotFound"));
const OrderDetail = lazy(() => import("./pages/OrderDetail"));
const Orders = lazy(() => import("./pages/Orders"));
const ProductDetail = lazy(() => import("./pages/ProductDetail"));
const Register = lazy(() => import("./pages/Register"));
const Shop = lazy(() => import("./pages/Shop"));
const Wishlist = lazy(() => import("./pages/Wishlist"));
const AdminCategories = lazy(() => import("./pages/admin/AdminCategories"));
const AdminCoupons = lazy(() => import("./pages/admin/AdminCoupons"));
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard"));
const AdminLayout = lazy(() => import("./pages/admin/AdminLayout"));
const AdminOrderDetail = lazy(
  () => import("./pages/admin/AdminOrderDetail")
);
const AdminOrders = lazy(() => import("./pages/admin/AdminOrders"));
const AdminReports = lazy(() => import("./pages/admin/AdminReports"));
const AdminReturns = lazy(() => import("./pages/admin/AdminReturns"));
const AdminProductForm = lazy(
  () => import("./pages/admin/AdminProductForm")
);
const AdminProducts = lazy(() => import("./pages/admin/AdminProducts"));

function RouteFallback() {
  return (
    <div
      role="status"
      className="flex min-h-[50vh] items-center justify-center text-gray-400"
    >
      Loading...
    </div>
  );
}

function App() {
  const [search, setSearch] = useState("");

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[60] focus:rounded-md focus:bg-cyan-400 focus:px-4 focus:py-2 focus:text-black"
      >
        Skip to content
      </a>

      <Suspense fallback={null}>
        <ParticleBackground />
      </Suspense>

      <div className="relative z-10 bg-black text-white min-h-screen pt-20">
        <Navbar search={search} setSearch={setSearch} />
        <Cart />

        <main id="main-content" tabIndex={-1}>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route
                path="/shop"
                element={<Shop search={search} setSearch={setSearch} />}
              />
              <Route path="/product/:slug" element={<ProductDetail />} />
              <Route path="/about" element={<About />} />
              <Route path="/contact" element={<Contact />} />
              <Route
                path="/checkout"
                element={
                  <ProtectedRoute>
                    <Checkout />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/orders"
                element={
                  <ProtectedRoute>
                    <Orders />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/wishlist"
                element={
                  <ProtectedRoute>
                    <Wishlist />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/orders/:orderId"
                element={
                  <ProtectedRoute>
                    <OrderDetail />
                  </ProtectedRoute>
                }
              />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forbidden" element={<Forbidden />} />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute adminOnly>
                    <AdminLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<AdminDashboard />} />
                <Route path="orders" element={<AdminOrders />} />
                <Route
                  path="orders/:orderId"
                  element={<AdminOrderDetail />}
                />
                <Route path="returns" element={<AdminReturns />} />
                <Route path="reports" element={<AdminReports />} />
                <Route path="products" element={<AdminProducts />} />
                <Route path="products/new" element={<AdminProductForm />} />
                <Route
                  path="products/:productId/edit"
                  element={<AdminProductForm />}
                />
                <Route path="categories" element={<AdminCategories />} />
                <Route path="coupons" element={<AdminCoupons />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </>
  );
}

export default App;
