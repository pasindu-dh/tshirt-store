import React from "react";

function About() {
  return (
    <div className="min-h-screen px-10 pt-18 pb-20">

      {/* TITLE */}
      <h1 className="text-4xl font-bold mt-10 mb-10 text-center scroll-mt-24">
        About Us
      </h1>

      {/* SECTION 1 — STORY */}
      <div className="grid md:grid-cols-2 gap-10 items-center">

        <img
          src="/about.jpg"
          alt="About"
          className="rounded-2xl w-full h-[400px] object-cover"
        />

        <div>
          <h2 className="text-2xl font-semibold mb-4">
            Who We Are
          </h2>

          <p className="text-gray-400 leading-7">
            FURZY is a modern streetwear brand focused on style, comfort, and individuality.
            We believe clothing is not just fashion — it's a way to express who you are.
          </p>

          <p className="text-gray-400 mt-4 leading-7">
            Our designs combine minimal aesthetics with bold identity,
            giving you confidence in every outfit.
          </p>
        </div>
      </div>



      {/* SECTION 2 — FEATURES */}
      <div className="mt-20 grid md:grid-cols-3 gap-8">

        <div className="bg-[#020617] border border-cyan-500/40 p-6 rounded-xl text-center shadow-[0_0_20px_rgba(34,211,238,0.2)]">
          <h3 className="text-xl font-semibold mb-2">Premium Quality</h3>
          <p className="text-gray-400">
            High-quality fabrics for long-lasting comfort.
          </p>
        </div>

        <div className="bg-[#020617] border border-cyan-500/40 p-6 rounded-xl text-center shadow-[0_0_20px_rgba(34,211,238,0.2)]">
          <h3 className="text-xl font-semibold mb-2">Modern Design</h3>
          <p className="text-gray-400">
            Trendy and minimal styles for everyday wear.
          </p>
        </div>

        <div className="bg-[#020617] border border-cyan-500/40 p-6 rounded-xl text-center shadow-[0_0_20px_rgba(34,211,238,0.2)]">
          <h3 className="text-xl font-semibold mb-2">Affordable</h3>
          <p className="text-gray-400">
            Premium look without high price.
          </p>
        </div>

      </div>

    </div>
  );
}

export default About;