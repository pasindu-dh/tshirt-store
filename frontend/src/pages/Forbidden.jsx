import { Link } from "react-router-dom";

function Forbidden() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-6">
      <h1 className="text-6xl font-extrabold text-cyan-400">403</h1>
      <p className="text-gray-400 mt-4">
        You do not have permission to view this page.
      </p>

      <Link
        to="/"
        className="mt-8 px-8 py-3 rounded-full bg-cyan-400 text-black font-semibold hover:bg-cyan-300 transition"
      >
        Back to home
      </Link>
    </div>
  );
}

export default Forbidden;
