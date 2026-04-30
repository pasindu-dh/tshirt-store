function Contact() {
  return (
    <div className="min-h-screen px-10 py-25 bg-[#020617] text-white">

      <h1 className="text-4xl font-bold mb-6 text-center">
        Contact Us
      </h1>

      <div className="max-w-xl mx-auto">

        <input
          type="text"
          placeholder="Your Name"
          className="w-full mb-4 p-3 rounded bg-[#111827]"
        />

        <input
          type="email"
          placeholder="Your email address"
          className="w-full mb-4 p-3 rounded bg-[#111827]"
        />

        <textarea
          placeholder="Your Message"
          className="w-full mb-4 p-3 rounded bg-[#111827]"
        />

        <button className="w-full bg-cyan-400 text-black py-3 rounded-lg">
          Send Message
        </button>

      </div>

    </div>
  );
}

export default Contact;