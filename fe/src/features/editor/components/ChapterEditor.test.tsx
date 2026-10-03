import type { Editor, JSONContent } from "@tiptap/core";
import { act, render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChapterEditor } from "./ChapterEditor";

function paragraphIds(editor: Editor): string[] {
  return editor.getJSON().content?.map((node) => String(node.attrs?.paragraph_id ?? "")) ?? [];
}

describe("ChapterEditor paragraph_id", () => {
  it("keeps the source ID and creates a unique 8-character ID when splitting", async () => {
    let editor: Editor | undefined;
    const content: JSONContent = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "abcd" }] }],
    };
    render(<ChapterEditor initialContent={content} onEditorReady={(instance) => { editor = instance; }} />);
    await waitFor(() => expect(editor).toBeDefined());

    const originalId = paragraphIds(editor!)[0];
    act(() => {
      editor!.commands.setTextSelection(3);
      editor!.commands.splitBlock();
    });
    const ids = paragraphIds(editor!);
    expect(ids).toHaveLength(2);
    expect(ids[0]).toBe(originalId);
    expect(new Set(ids).size).toBe(2);
    expect(ids.every((id) => /^[a-z0-9]{8}$/.test(id))).toBe(true);
  });

  it("keeps unique IDs and the upper paragraph ID after merging", async () => {
    let editor: Editor | undefined;
    const content: JSONContent = {
      type: "doc",
      content: [
        { type: "paragraph", content: [{ type: "text", text: "upper" }] },
        { type: "paragraph", content: [{ type: "text", text: "lower" }] },
      ],
    };
    render(<ChapterEditor initialContent={content} onEditorReady={(instance) => { editor = instance; }} />);
    await waitFor(() => expect(editor).toBeDefined());

    const originalIds = paragraphIds(editor!);
    act(() => {
      editor!.commands.setTextSelection(8);
      editor!.commands.joinBackward();
    });
    const ids = paragraphIds(editor!);
    expect(ids).toHaveLength(1);
    expect(ids[0]).toBe(originalIds[0]);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
