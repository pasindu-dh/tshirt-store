import { useState } from "react";

function Contact() {
  const [status, setStatus] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);

    const res = await fetch("https://formspree.io/f/maqvnewn", {
      method: "POST",
      body: formData,
      headers: {
        Accept: "application/json",
      },
    });

    if (res.ok) {
      setStatus("SUCCESS");
      e.target.reset();
    } else {
      setStatus("ERROR");
    }
  };

  return (
    <div className="min-h-screen px-10 pt-18 pb-20">

      <h1 className="text-4xl font-bold mt-10 mb-10 text-center scroll-mt-24">
        Contact Us
      </h1>

      <form
        onSubmit={handleSubmit}
        className="max-w-xl mx-auto space-y-6"
      >

        <input
          type="text"
          name="name"
          placeholder="Your Name"
          required
          className="w-full p-3 rounded bg-[#020617] border border-gray-700"
        />

        <input
          type="email"
          name="email"
          placeholder="Your Email"
          required
          className="w-full p-3 rounded bg-[#020617] border border-gray-700"
        />

        <textarea
          name="message"
          placeholder="Your Message"
          required
          rows="5"
          className="w-full p-3 rounded bg-[#020617] border border-gray-700"
        />

        <button
          type="submit"
          className="w-full bg-cyan-400 text-black py-3 rounded-lg hover:bg-cyan-300 transition"
        >
          Send Message
        </button>

        {/* STATUS */}
        {status === "SUCCESS" && (
          <p className="text-green-400 text-center">
            Message sent successfully!
          </p>
        )}

        {status === "ERROR" && (
          <p className="text-red-400 text-center">
            Something went wrong.
          </p>
        )}

      </form>
    </div>
  );
}

export default Contact;