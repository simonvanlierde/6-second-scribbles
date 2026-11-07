import { fireEvent, render } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import StepperInput from "./fixtures/StepperHarness.svelte";

describe("StepperInput", () => {
  it("increments and decrements within range", async () => {
    const { container } = render(StepperInput);
    await fireEvent.click(container.querySelector('[aria-label="Increase Rounds"]')!);
    expect(container.querySelector("output")?.textContent).toBe("6");
    await fireEvent.click(container.querySelector('[aria-label="Decrease Rounds"]')!);
    expect(container.querySelector("output")?.textContent).toBe("5");
  });

  it("updates only valid typed values and clamps on blur", async () => {
    const { container } = render(StepperInput);
    const input = container.querySelector("input")!;
    await fireEvent.input(input, { target: { value: "8" } });
    expect(container.querySelector("output")?.textContent).toBe("8");
    await fireEvent.input(input, { target: { value: "99" } });
    expect(container.textContent).toContain("Must be between 1 and 10");
    await fireEvent.blur(input);
    expect(container.querySelector("output")?.textContent).toBe("10");
  });
});
