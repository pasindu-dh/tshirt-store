import { imageUrl } from "../../api/client";

function ImageManager({
  images,
  uploading,
  onUpload,
  onRemove,
  onMakePrimary,
}) {
  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <label
          className={`inline-flex justify-center cursor-pointer bg-cyan-400 text-black px-4 py-2 rounded-lg font-semibold hover:bg-cyan-300 transition ${
            uploading ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          {uploading ? "Uploading..." : "Upload images"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={onUpload}
            className="hidden"
          />
        </label>

        <span className="text-sm text-gray-400">
          JPEG, PNG or WebP, up to 5 MB each.
        </span>
      </div>

      {images.length === 0 ? (
        <p className="text-gray-500 text-sm mt-4">No images yet.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
          {images.map((url, index) => (
            <div
              key={`${url}-${index}`}
              className="bg-black border border-gray-800 rounded-xl overflow-hidden"
            >
              <div className="relative">
                <img
                  src={imageUrl(url)}
                  alt={`Product image ${index + 1}`}
                  className="w-full h-32 object-cover"
                />

                {index === 0 && (
                  <span className="absolute top-2 left-2 bg-cyan-400 text-black text-xs px-2 py-0.5 rounded-full">
                    Primary
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between gap-2 p-2">
                {index > 0 ? (
                  <button
                    type="button"
                    onClick={() => onMakePrimary(index)}
                    className="text-xs text-cyan-400 hover:text-cyan-300"
                  >
                    Make primary
                  </button>
                ) : (
                  <span />
                )}

                <button
                  type="button"
                  onClick={() => onRemove(index)}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ImageManager;
