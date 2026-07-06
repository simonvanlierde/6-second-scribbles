import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AllDrawingsGallery from "@/components/results/AllDrawingsGallery.vue";
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
    const wrapper = mount(AllDrawingsGallery, { props: { drawings } });
    expect(wrapper.findAll(".gallery__cell")).toHaveLength(3);
  });

  it("shows an empty state when there are no drawings", () => {
    const wrapper = mount(AllDrawingsGallery, { props: { drawings: [] } });
    expect(wrapper.findAll(".gallery__cell")).toHaveLength(0);
    expect(wrapper.find(".gallery__empty").exists()).toBe(true);
  });

  it("downloads the matching drawing when its button is clicked", async () => {
    const wrapper = mount(AllDrawingsGallery, { props: { drawings } });

    const buttons = wrapper.findAll(".gallery__download");
    expect(buttons).toHaveLength(3);
    await buttons[1]?.trigger("click");

    expect(exportDrawingMock).toHaveBeenCalledTimes(1);
    expect(exportDrawingMock.mock.calls[0]?.[0]).toBe("data:image/png;base64,A2");
    // Filename is slugged from name + round and ends in .png.
    expect(exportDrawingMock.mock.calls[0]?.[1]).toMatch(/alice.*2.*\.png$/i);
  });

  it("gives each download button a descriptive aria-label", () => {
    const wrapper = mount(AllDrawingsGallery, { props: { drawings } });
    const label = wrapper.find(".gallery__download").attributes("aria-label");
    expect(label).toContain("Alice");
  });
});
