import { Extension } from "@tiptap/core";
import { Plugin } from "@tiptap/pm/state";

import { normalizeVietnameseText } from "@/shared/lib/vi";

/** Normalize pasted text and HTML while leaving editor composition untouched. */
export const PasteNormalize = Extension.create({
  name: "pasteNormalize",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        props: {
          transformPastedText: (text) => normalizeVietnameseText(text),
          transformPastedHTML: (html) => normalizeVietnameseText(html),
        },
      }),
    ];
  },
});
