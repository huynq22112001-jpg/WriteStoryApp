import { diffVietnameseWords } from "./wordDiff";

type Request = { id: number; before: string; after: string };

self.onmessage = (event: MessageEvent<Request>) => {
  const { id, before, after } = event.data;
  const parts = diffVietnameseWords(before, after);
  self.postMessage({ id, parts });
};
