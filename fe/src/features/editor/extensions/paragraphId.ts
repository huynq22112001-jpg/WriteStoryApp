import { UniqueID } from "@tiptap/extension-unique-id";

const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";

export function newParagraphId(): string {
  const bytes = new Uint8Array(8);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join("");
}

export const paragraphIdExtension = UniqueID.configure({
  attributeName: "paragraph_id",
  types: ["paragraph", "heading", "horizontalRule"],
  generateID: newParagraphId,
});
