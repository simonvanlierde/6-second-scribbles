import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSettingsPanel } from "@/composables/useSettingsPanel.svelte";

describe("useSettingsPanel", () => {
  beforeEach(() => {
    useSettingsPanel().close();
  });

  it("opens the regular settings panel without a pending action", () => {
    const panel = useSettingsPanel();

    panel.open();

    expect(panel.isOpen).toBe(true);
    expect(panel.focusNameOnOpen).toBe(false);
    expect(panel.pendingNameAction).toBeNull();
  });

  it("opens for name entry with an optional action to resume", () => {
    const action = vi.fn();
    const panel = useSettingsPanel();

    panel.openForName(action);

    expect(panel.isOpen).toBe(true);
    expect(panel.focusNameOnOpen).toBe(true);
    expect(panel.pendingNameAction).toBe(action);
  });

  it("clears transient name-entry state when closed", () => {
    const panel = useSettingsPanel();
    panel.openForName(vi.fn());

    panel.close();

    expect(panel.isOpen).toBe(false);
    expect(panel.focusNameOnOpen).toBe(false);
    expect(panel.pendingNameAction).toBeNull();
  });
});
