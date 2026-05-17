// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { mount, tick, unmount } from "svelte";
import type { Message } from "../../api/types.js";
// @ts-ignore
import MessageContent from "./MessageContent.svelte";

vi.mock("../../stores/messages.svelte.js", () => ({
  messages: {
    sessionId: "",
    mainModel: "",
  },
}));

vi.mock("../../stores/ui.svelte.js", () => ({
  ui: {
    isBlockVisible: () => true,
  },
}));

vi.mock("../../stores/pins.svelte.js", () => ({
  pins: {
    isPinned: () => false,
    togglePin: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock("../../stores/sessions.svelte.js", () => ({
  sessions: {
    sessions: [],
    activeSession: null,
  },
}));

vi.mock("../../utils/highlight.js", () => ({
  applyHighlight: () => {},
  escapeHTML: (value: string) => value,
}));

vi.mock("../../utils/clipboard.js", () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}));

type MessageWithTokenFlags = Message & {
  has_context_tokens?: boolean;
  has_output_tokens?: boolean;
};

function makeMessage(
  overrides: Partial<MessageWithTokenFlags> = {},
): MessageWithTokenFlags {
  return {
    id: 1,
    session_id: "session-1",
    ordinal: 0,
    role: "assistant",
    content: "Token summary",
    timestamp: "2026-02-20T12:30:00Z",
    has_thinking: false,
    thinking_text: "",
    has_tool_use: false,
    content_length: 13,
    model: "claude-sonnet",
    token_usage: null,
    context_tokens: 0,
    output_tokens: 0,
    is_system: false,
    ...overrides,
  };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("MessageContent", () => {
  it("renders compact token totals when both token metrics are reported", async () => {
    const component = mount(MessageContent, {
      target: document.body,
      props: {
        message: makeMessage({
          context_tokens: 2400,
          output_tokens: 180,
          has_context_tokens: true,
          has_output_tokens: true,
        }),
      },
    });

    await tick();
    const tokenMeta = document.querySelector(".message-tokens");
    expect(tokenMeta?.textContent?.replace(/\s+/g, " ").trim()).toBe(
      "2.4k ctx / 180 out",
    );

    unmount(component);
  });

  it("renders an explicit missing token placeholder when context tokens are absent", async () => {
    const component = mount(MessageContent, {
      target: document.body,
      props: {
        message: makeMessage({
          context_tokens: 0,
          output_tokens: 180,
          has_context_tokens: false,
          has_output_tokens: true,
        }),
      },
    });

    await tick();
    const tokenMeta = document.querySelector(".message-tokens");
    expect(tokenMeta?.textContent?.replace(/\s+/g, " ").trim()).toBe(
      "— ctx / 180 out",
    );

    unmount(component);
  });

  it("renders codex bash output in a structured tool block without duplicate markdown command text", async () => {
    const component = mount(MessageContent, {
      target: document.body,
      props: {
        message: makeMessage({
          content: "[Bash]\n$ curl http://example.test",
          has_tool_use: true,
          content_length: 34,
          tool_calls: [
            {
              tool_name: "exec_command",
              category: "Bash",
              input_json: JSON.stringify({ cmd: "curl http://example.test" }),
              result_content: "HTTP/1.1 200 OK\nctfhub{demo-flag}",
            },
          ],
        }),
      },
    });

    await tick();

    const markdownBlocks = Array.from(document.querySelectorAll(".text-content"));
    expect(markdownBlocks).toHaveLength(0);

    const toolLabel = document.querySelector(".tool-label");
    expect(toolLabel?.textContent).toBe("Bash");

    const outputHeader = document.querySelector<HTMLButtonElement>(".output-header");
    expect(outputHeader).not.toBeNull();
    expect(outputHeader?.textContent).toContain("HTTP/1.1 200 OK");

    outputHeader!.click();
    await tick();

    const outputContent = document.querySelector(".output-content");
    expect(outputContent).not.toBeNull();
    expect(outputContent!.textContent).toContain("HTTP/1.1 200 OK");
    expect(outputContent!.textContent).toContain("ctfhub{demo-flag}");

    unmount(component);
  });

  it("renders cairn conclusion json as a structured summary card", async () => {
    const component = mount(MessageContent, {
      target: document.body,
      props: {
        message: makeMessage({
          content: JSON.stringify({
            accepted: true,
            data: {
              fact: {
                description: "Confirmed SSRF bypass via numeric loopback and recovered ctfhub{demo-flag}.",
              },
              complete: {
                description: "The project goal was to obtain the flag, and the application returned it directly.",
              },
            },
          }),
        }),
      },
    });

    await tick();

    const card = document.querySelector(".conclusion-card");
    expect(card).not.toBeNull();
    expect(card?.textContent).toContain("已完成");
    expect(card?.textContent).toContain("已确认事实");
    expect(card?.textContent).toContain("完成原因");
    expect(card?.textContent).toContain("numeric loopback");
    expect(card?.textContent).toContain("returned it directly");

    const rawJson = document.body.textContent ?? "";
    expect(rawJson).not.toContain('{"accepted":true');

    unmount(component);
  });
});
