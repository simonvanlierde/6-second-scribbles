import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AllDrawingsGallery from "@/components/results/AllDrawingsGallery.svelte";
import type { GalleryDrawing } from "@/shared/types";

const exportDrawingMock = vi.fn();

vi.mock("@/composables/useDrawingExport", () => ({
  useDrawingExport: () => ({ exportDrawing: exportDrawingMock }),
}));

const drawings: GalleryDrawing[] = [
  {
    round: 1,
    playerId: "p1",
    name: "Alice",
    color: "#ffb4a2",
    drawing: "data:image/png;base64,A1",
  },
  {
    round: 2,
    playerId: "p1",
    name: "Alice",
    color: "#ffb4a2",
    drawing: "data:image/png;base64,A2",
  },
  {
    round: 1,
    playerId: "p2",
    name: "Bob",
    color: "#b5e6b5",
    drawing: "data:image/png;base64,B1",
  },
];

beforeEach(() => {
  exportDrawingMock.mockClear();
});

describe("AllDrawingsGallery", () => {
  it("renders one cell per drawing", () => {
    const wrapper = render(AllDrawingsGallery, { props: { drawings } });
    expect(Array.from(wrapper.container.querySelectorAll(".gallery__cell"))).toHaveLength(3);
  });

  it("shows an empty state when there are no drawings", () => {
    const wrapper = render(AllDrawingsGallery, { props: { drawings: [] } });
    expect(Array.from(wrapper.container.querySelectorAll(".gallery__cell"))).toHaveLength(0);
    expect(wrapper.container.querySelector(".gallery__empty")! !== null).toBe(true);
  });

  it("downloads the matching drawing when its button is clicked", async () => {
    const wrapper = render(AllDrawingsGallery, { props: { drawings } });

    const buttons = Array.from(wrapper.container.querySelectorAll(".gallery__download"));
    expect(buttons).toHaveLength(3);
    await fireEvent.click(buttons[1]!);

    expect(exportDrawingMock).toHaveBeenCalledTimes(1);
    expect(exportDrawingMock.mock.calls[0]?.[0]).toBe("data:image/png;base64,A2");
    // Filename is slugged from name + round and ends in .png.
    expect(exportDrawingMock.mock.calls[0]?.[1]).toMatch(/alice.*2.*\.png$/i);
  });

  it("gives each download button a descriptive aria-label", () => {
    const wrapper = render(AllDrawingsGallery, { props: { drawings } });
    const label = wrapper.container.querySelector(".gallery__download")?.getAttribute("aria-label");
    expect(label).toContain("Alice");
  });
});
