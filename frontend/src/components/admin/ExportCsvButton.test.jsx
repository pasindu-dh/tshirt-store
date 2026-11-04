import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ExportCsvButton from "./ExportCsvButton";

describe("ExportCsvButton", () => {
  it("calls the export handler", async () => {
    const onExport = vi.fn().mockResolvedValue();

    render(
      <ExportCsvButton
        label="Export orders CSV"
        onExport={onExport}
      />
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Export orders CSV",
      })
    );

    expect(onExport).toHaveBeenCalledTimes(1);
    expect(
      await screen.findByRole("button", {
        name: "Export orders CSV",
      })
    ).toBeEnabled();
  });

  it("shows an API error when the export fails", async () => {
    const onExport = vi.fn().mockRejectedValue({
      response: { data: { detail: "Export failed." } },
    });

    render(<ExportCsvButton onExport={onExport} />);

    fireEvent.click(
      screen.getByRole("button", { name: "Export CSV" })
    );

    expect(
      await screen.findByText("Export failed.")
    ).toBeInTheDocument();
  });
});
