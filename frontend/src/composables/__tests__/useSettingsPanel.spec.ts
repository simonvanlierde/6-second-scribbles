import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSettingsPanel } from "@/composables/useSettingsPanel";

describe("useSettingsPanel", () => {
  beforeEach(() => {
    useSettingsPanel().close();
  });

  it("opens the regular settings panel without a pending action", () => {
    const panel = useSettingsPanel();

    panel.open();

    expect(panel.isOpen.value).toBe(true);
    expect(panel.focusNameOnOpen.value).toBe(false);
    expect(panel.pendingNameAction.value).toBeNull();
  });

  it("opens for name entry with an optional action to resume", () => {
    const action = vi.fn();
    const panel = useSettingsPanel();

    panel.openForName(action);

    expect(panel.isOpen.value).toBe(true);
    expect(panel.focusNameOnOpen.value).toBe(true);
    expect(panel.pendingNameAction.value).toBe(action);
  });

  it("clears transient name-entry state when closed", () => {
    const panel = useSettingsPanel();
    panel.openForName(vi.fn());

    panel.close();

    expect(panel.isOpen.value).toBe(false);
    expect(panel.focusNameOnOpen.value).toBe(false);
    expect(panel.pendingNameAction.value).toBeNull();
  });
});
