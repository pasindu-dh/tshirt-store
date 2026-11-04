import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AdminCatalogImport from "./AdminCatalogImport";
import {
  applyCatalogImport,
  previewCatalogImport,
} from "../../api/adminCatalogImport";

vi.mock("../../api/adminCatalogImport", () => ({
  previewCatalogImport: vi.fn(),
  applyCatalogImport: vi.fn(),
}));

vi.mock("../../api/adminExports", () => ({
  downloadCatalogCsv: vi.fn(),
}));

const RESULT = {
  dry_run: true,
  valid: true,
  summary: {
    total_rows: 2,
    valid_rows: 2,
    error_rows: 0,
    products_create: 1,
    products_update: 0,
    variants_create: 2,
    variants_update: 0,
  },
  rows: [
    {
      row: 2,
      action: "create",
      product_name: "Imported Tee",
      product_slug: "",
      variant: "M / Black",
      message: "Variant will be created.",
    },
    {
      row: 3,
      action: "create",
      product_name: "Imported Tee",
      product_slug: "",
      variant: "L / Black",
      message: "Variant will be created.",
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminCatalogImport />
    </MemoryRouter>
  );
}

function chooseFile() {
  const file = new File(
    ["product_slug,product_name\n,Imported Tee\n"],
    "catalog.csv",
    { type: "text/csv" }
  );

  fireEvent.change(screen.getByLabelText("Catalog CSV"), {
    target: { files: [file] },
  });

  return file;
}

describe("AdminCatalogImport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    previewCatalogImport.mockResolvedValue(RESULT);
    applyCatalogImport.mockResolvedValue({
      ...RESULT,
      dry_run: false,
    });
  });

  it("previews, then applies a valid catalog import", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();

    const file = chooseFile();
    fireEvent.click(
      screen.getByRole("button", { name: "Preview CSV" })
    );

    await waitFor(() => {
      expect(previewCatalogImport).toHaveBeenCalledWith(file);
    });
    expect(
      (await screen.findAllByText("Imported Tee")).length
    ).toBeGreaterThan(0);
    expect(screen.getByText("New products")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Apply import" })
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Apply import" })
    );

    await waitFor(() => {
      expect(applyCatalogImport).toHaveBeenCalledWith(file);
    });
    expect(
      await screen.findByText(/Import applied successfully/)
    ).toBeInTheDocument();
  });

  it("shows validation errors and blocks apply", async () => {
    previewCatalogImport.mockResolvedValue({
      ...RESULT,
      valid: false,
      summary: {
        ...RESULT.summary,
        valid_rows: 1,
        error_rows: 1,
      },
      rows: [
        {
          row: 2,
          action: "error",
          product_name: "Bad Tee",
          product_slug: "",
          variant: "M / Black",
          message: "price must be a whole number.",
        },
      ],
    });

    renderPage();
    chooseFile();
    fireEvent.click(
      screen.getByRole("button", { name: "Preview CSV" })
    );

    expect(
      await screen.findByText("price must be a whole number.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Fix the listed row errors and upload again."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Apply import" })
    ).not.toBeInTheDocument();
  });
});
