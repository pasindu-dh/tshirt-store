export function getApiError(
  error,
  fallback = "Something went wrong. Please try again."
) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((message) => typeof message === "string" && message.length > 0);

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  if (error?.code === "ECONNABORTED") {
    return "The server took too long to respond. Please try again.";
  }

  if (
    error?.code === "ERR_NETWORK" ||
    (!error?.response && Boolean(error?.request))
  ) {
    return "Cannot reach the server. Check that the backend is running and try again.";
  }

  return fallback;
}
