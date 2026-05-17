import { describe, expect, it } from "vitest";
import { parseCairnTitleBadge } from "./cairn-title-badges.js";

describe("parseCairnTitleBadge", () => {
  it("parses fact titles for Cairn projects", () => {
    expect(
      parseCairnTitleBadge(
        "cairn:proj_033",
        "事实: 已确认 file:// 对不存在文件返回错误",
        false,
      ),
    ).toEqual({
      kind: "fact",
      label: "事实",
      text: "已确认 file:// 对不存在文件返回错误",
    });
  });

  it("parses all supported Cairn prefixes", () => {
    expect(
      parseCairnTitleBadge("cairn:proj_1", "计划: 找到 flag", false),
    )?.toMatchObject({ kind: "plan", label: "计划", text: "找到 flag" });
    expect(
      parseCairnTitleBadge("cairn:proj_1", "探索: 尝试 redis://", false),
    )?.toMatchObject({ kind: "explore", label: "探索", text: "尝试 redis://" });
    expect(
      parseCairnTitleBadge("cairn:proj_1", "起步: 读取题面", false),
    )?.toMatchObject({ kind: "bootstrap", label: "起步", text: "读取题面" });
    expect(
      parseCairnTitleBadge("cairn:proj_1", "完成: 拿到 flag", false),
    )?.toMatchObject({ kind: "done", label: "完成", text: "拿到 flag" });
  });

  it("keeps unmatched Cairn titles unchanged by returning null", () => {
    expect(
      parseCairnTitleBadge("cairn:proj_033", "直接保留原标题", false),
    ).toBeNull();
  });

  it("does not apply badges to non-Cairn projects", () => {
    expect(
      parseCairnTitleBadge(
        "test-project",
        "事实: 这个标题不该被加 badge",
        false,
      ),
    ).toBeNull();
  });

  it("does not apply badges to shell-style titles", () => {
    expect(
      parseCairnTitleBadge("cairn:proj_033", "事实: echo hello", true),
    ).toBeNull();
  });
});
