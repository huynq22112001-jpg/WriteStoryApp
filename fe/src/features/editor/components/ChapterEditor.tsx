import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/react";
import type { Editor, JSONContent } from "@tiptap/core";
import { useEffect, useState } from "react";

import { countVietnameseSyllables } from "@/shared/lib/vi";

import { paragraphIdExtension } from "../extensions/paragraphId";
import { PasteNormalize } from "../extensions/pasteNormalize";

export interface ChapterEditorProps {
  initialContent?: JSONContent;
  onEditorReady?: (editor: Editor) => void;
  onChange?: (doc: JSONContent) => void;
  editable?: boolean;
}

const emptyDocument: JSONContent = {
  type: "doc",
  content: [{ type: "paragraph" }],
};

export function ChapterEditor({ initialContent = emptyDocument, onEditorReady, onChange, editable = true }: ChapterEditorProps) {
  const [metrics, setMetrics] = useState({ syllables: 0, characters: 0 });
  const editor = useEditor({
    extensions: [StarterKit, paragraphIdExtension, PasteNormalize],
    content: initialContent,
    editable,
    shouldRerenderOnTransaction: false,
    editorProps: {
      attributes: {
        "aria-label": "Nội dung chương",
        class: "min-h-80 rounded-md border border-stone-300 bg-white p-5 font-serif text-lg leading-8 outline-none",
      },
    },
    onCreate: ({ editor: createdEditor }) => {
      onEditorReady?.(createdEditor);
      const text = createdEditor.getText();
      setMetrics({ syllables: countVietnameseSyllables(text), characters: Array.from(text).length });
    },
    onUpdate: ({ editor: updatedEditor }) => {
      const text = updatedEditor.getText();
      setMetrics({ syllables: countVietnameseSyllables(text), characters: Array.from(text).length });
      onChange?.(updatedEditor.getJSON());
    },
  });

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(editable);
  }, [editor, editable]);

  useEffect(() => {
    if (!editor) return;
    const current = JSON.stringify(editor.getJSON());
    const incoming = JSON.stringify(initialContent);
    if (current !== incoming) editor.commands.setContent(initialContent, { emitUpdate: false });
  }, [editor, initialContent]);

  return (
    <section className="mx-auto w-full max-w-4xl p-6" data-testid="chapter-editor" aria-readonly={!editable}>
      <div className="mb-3 flex gap-2" aria-label="Định dạng văn bản">
        <button
          type="button"
          aria-label="In đậm"
          aria-pressed={editor?.isActive("bold") ?? false}
          className="rounded border px-3 py-1"
          onClick={() => editor?.chain().focus().toggleBold().run()}
        >
          B
        </button>
        <button
          type="button"
          aria-label="In nghiêng"
          aria-pressed={editor?.isActive("italic") ?? false}
          className="rounded border px-3 py-1 italic"
          onClick={() => editor?.chain().focus().toggleItalic().run()}
        >
          I
        </button>
        <button type="button" aria-label="Tiêu đề cấp 1" aria-pressed={editor?.isActive("heading", { level: 1 }) ?? false} className="rounded border px-3 py-1 text-sm" onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}>H1</button>
        <button type="button" aria-label="Tiêu đề cấp 2" aria-pressed={editor?.isActive("heading", { level: 2 }) ?? false} className="rounded border px-3 py-1 text-sm" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>H2</button>
        <button type="button" aria-label="Trích dẫn" aria-pressed={editor?.isActive("blockquote") ?? false} className="rounded border px-3 py-1 text-sm" onClick={() => editor?.chain().focus().toggleBlockquote().run()}>❝</button>
        <button type="button" aria-label="Ngắt cảnh" className="rounded border px-3 py-1 text-sm" onClick={() => editor?.chain().focus().setHorizontalRule().run()}>* * *</button>
      </div>
      <EditorContent editor={editor} />
      <output className="mt-2 block text-sm text-stone-600" aria-label="Độ dài văn bản">
        {metrics.syllables} âm tiết · {metrics.characters} ký tự
      </output>
    </section>
  );
}
