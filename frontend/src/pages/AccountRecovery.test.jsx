import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";
import VerifyEmail from "./VerifyEmail";
import {
  requestPasswordReset,
  resendEmailVerification,
  resetPassword,
  verifyEmail,
} from "../api/auth";

vi.mock("../api/auth", () => ({
  requestPasswordReset: vi.fn(),
  resetPassword: vi.fn(),
  resendEmailVerification: vi.fn(),
  verifyEmail: vi.fn(),
}));

const authMocks = vi.hoisted(() => ({
  refreshUser: vi.fn().mockResolvedValue(null),
}));

vi.mock("../hooks/useAuth", () => ({
  default: () => ({
    user: null,
    loading: false,
    isAuthenticated: false,
    refreshUser: authMocks.refreshUser,
  }),
}));

describe("account recovery pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    requestPasswordReset.mockResolvedValue({
      message: "If an account exists, an email has been sent.",
    });
    resetPassword.mockResolvedValue({
      message: "Your password has been reset.",
    });
    resendEmailVerification.mockResolvedValue({
      message: "A new verification link has been sent.",
    });
    verifyEmail.mockResolvedValue({
      message: "Your email address has been verified.",
    });
  });

  it("requests a password reset", async () => {
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "customer@furzy.dev" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Send reset link" })
    );

    await waitFor(() => {
      expect(requestPasswordReset).toHaveBeenCalledWith(
        "customer@furzy.dev"
      );
    });
    expect(
      await screen.findByText(
        "If an account exists, an email has been sent."
      )
    ).toBeInTheDocument();
  });

  it("resets a password with a token", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/reset-password?token=reset-token-for-testing",
        ]}
      >
        <ResetPassword />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass123!" },
    });
    fireEvent.change(
      screen.getByLabelText("Confirm new password"),
      { target: { value: "NewPass123!" } }
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Set new password" })
    );

    await waitFor(() => {
      expect(resetPassword).toHaveBeenCalledWith(
        "reset-token-for-testing",
        "NewPass123!"
      );
    });
    expect(
      await screen.findByText("Your password has been reset.")
    ).toBeInTheDocument();
  });

  it("rejects mismatched passwords locally", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/reset-password?token=reset-token-for-testing",
        ]}
      >
        <ResetPassword />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass123!" },
    });
    fireEvent.change(
      screen.getByLabelText("Confirm new password"),
      { target: { value: "DifferentPass123!" } }
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Set new password" })
    );

    expect(
      screen.getByText("Passwords do not match.")
    ).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("verifies an email token on load", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/verify-email?token=verify-token-for-testing",
        ]}
      >
        <VerifyEmail />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(verifyEmail).toHaveBeenCalledWith(
        "verify-token-for-testing"
      );
    });
    expect(
      await screen.findByText(
        "Your email address has been verified."
      )
    ).toBeInTheDocument();
  });

  it("resends a verification link", async () => {
    render(
      <MemoryRouter>
        <VerifyEmail />
      </MemoryRouter>
    );

    fireEvent.change(
      screen.getByLabelText("Account email"),
      { target: { value: "customer@furzy.dev" } }
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Send a new verification link",
      })
    );

    await waitFor(() => {
      expect(resendEmailVerification).toHaveBeenCalledWith(
        "customer@furzy.dev"
      );
    });
    expect(
      await screen.findByText(
        "A new verification link has been sent."
      )
    ).toBeInTheDocument();
  });
});
