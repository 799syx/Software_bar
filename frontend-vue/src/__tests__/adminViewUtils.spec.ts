import { describe, expect, it } from "vitest";
import { distributionCount, mergeNumericDistributions, percentNumber } from "../components/admin/adminViewUtils";

describe("admin report sentiment helpers", () => {
  it("keeps positive rating sentiment when interaction sentiment already exists", () => {
    const merged = mergeNumericDistributions(
      { neutral: 3 },
      { positive: 5, neutral: 2, negative: 1 }
    );
    const total = Object.values(merged).reduce((sum, value) => sum + value, 0);

    expect(merged).toEqual({ neutral: 5, positive: 5, negative: 1 });
    expect(distributionCount(merged, ["positive"])).toBe(5);
    expect(percentNumber(distributionCount(merged, ["positive"]), total)).toBe(45);
  });
});
