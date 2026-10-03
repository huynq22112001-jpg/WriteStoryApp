import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import type { JSONContent } from "@tiptap/core";
import type { Editor } from "@tiptap/core";
import { useHotkeys } from "react-hotkeys-hook";
import { BookPlus, Focus, History, PanelRightClose, PanelRightOpen, Save } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/states";
import { currentSession, createApiClient } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import { isTauri } from "@/shared/desktop/bridge";
import { ChapterEditor } from "./ChapterEditor";
import { diffVietnameseWords } from "../workers/wordDiff";

type Chapter = { id: string; chapter_no: number; title: string; current_revision_id: string | null; revision_count: number; syllable_count: number; status: string; is_base_locked?: boolean };
type Copy = { chapter_id: string; base_revision_id: string | null; doc_json: JSONContent; has_changes: boolean; client_session_id: string | null; client_seq: number };
type Revision = { id: string; revision_no: number; reason: string; source: string; created_at: string; plain_text: string; paragraphs: { id: string; text: string }[] };
const EMPTY_DOC: JSONContent = { type: "doc", content: [{ type: "paragraph" }] };
const sessionId = crypto.randomUUID();

async function saveWorkingCopyWithRetry<T>(operation: () => Promise<T>): Promise<T> {
  let delayMs = 1000;
  for (let attempt = 0; ; attempt += 1) {
    try { return await operation(); }
    catch (error) {
      if (error instanceof ApiError && [409, 423].includes(error.status)) throw error;
      if (attempt >= 6) throw error;
      await new Promise((resolve) => window.setTimeout(resolve, delayMs));
      delayMs = Math.min(delayMs * 2, 30_000);
    }
  }
}

export function WorkspacePage() {
  const { workId } = useParams({ from: "/works/$workId" });
  const session = currentSession();
  const api = session ? createApiClient(session) : null;
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [doc, setDoc] = useState<JSONContent | null>(null);
  const latestDocRef = useRef<JSONContent | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const allowCloseRef = useRef(false);
  const saveInFlightRef = useRef(false);
  const latestFlushRef = useRef<{ chapterId: string | null; flush: (reason: "leave_chapter") => Promise<boolean> }>({ chapterId: null, flush: async () => false });
  const [dirty, setDirty] = useState(false);
  const [seq, setSeq] = useState(0);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [historyDiff, setHistoryDiff] = useState<{ before: string; after: string; parts?: ReturnType<typeof diffVietnameseWords> } | null>(null);
  const diffWorkerRef = useRef<Worker | null>(null);
  const diffRequestRef = useRef(0);
  const [focus, setFocus] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [saveBlocked, setSaveBlocked] = useState(false);
  const [pausingForEdit, setPausingForEdit] = useState(false);
  const [pauseRequested, setPauseRequested] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [treeOpen, setTreeOpen] = useState(true);
  const [leftWidth, setLeftWidth] = useState(224);
  const [rightWidth, setRightWidth] = useState(320);
  const [tab, setTab] = useState<"ai" | "characters" | "memory" | "handoff" | "review" | "history">("ai");
  const [mode, setMode] = useState<"outline" | "write" | "review" | "bible">("write");
  const chaptersQuery = useQuery({ queryKey: ["chapters", workId], enabled: !!api, queryFn: () => api!.get<Chapter[]>(`/v1/works/${workId}/chapters`) });
  const chapters = chaptersQuery.data ?? [];
  const activeId = selectedId ?? chapters[0]?.id ?? null;
  const copyQuery = useQuery({ queryKey: ["working-copy", activeId], enabled: !!api && !!activeId, queryFn: () => api!.get<Copy>(`/v1/chapters/${activeId}/working-copy`) });
  const activeChapterQuery = useQuery({ queryKey: ["chapter", activeId], enabled: !!api && !!activeId, queryFn: () => api!.get<Chapter>(`/v1/chapters/${activeId}`) });
  const revisionsQuery = useQuery({ queryKey: ["revisions", activeId], enabled: !!api && !!activeId && tab === "history", queryFn: () => api!.get<Revision[]>(`/v1/chapters/${activeId}/revisions`) });
  const initialDoc = useMemo(() => doc ?? copyQuery.data?.doc_json ?? EMPTY_DOC, [doc, copyQuery.data]);

  async function flushDraft(snapshotReason?: "leave_chapter" | "manual_snapshot" | "idle") {
    if (!api || !activeId || !doc) return false;
    try {
      if (dirty) {
        const nextSeq = seq + 1;
        await api.put(`/v1/chapters/${activeId}/working-copy`, {
          doc_json: doc,
          base_revision_id: copyQuery.data?.base_revision_id ?? chapters.find((chapter) => chapter.id === activeId)?.current_revision_id ?? null,
          client_session_id: sessionId,
          client_seq: nextSeq,
        });
        setSeq(nextSeq);
        setDirty(false);
        setSavedAt(new Date().toLocaleTimeString());
      }
      if (snapshotReason) {
        await api.post(`/v1/chapters/${activeId}/snapshot`, { reason: snapshotReason, expected_revision: chapters.find((chapter) => chapter.id === activeId)?.revision_count ?? 0 });
        await queryClient.invalidateQueries({ queryKey: ["revisions", activeId] });
        await queryClient.invalidateQueries({ queryKey: ["chapters", workId] });
        toast.success("Đã tạo phiên bản mới");
      }
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) setConflict(true);
      toast.error("Chưa lưu được bản nháp. Nội dung hiện còn trong cửa sổ này.");
      return false;
    }
  }

  latestFlushRef.current = { chapterId: activeId, flush: (reason) => flushDraft(reason) };
  useEffect(() => {
    const chapterId = activeId;
    return () => {
      if (latestFlushRef.current.chapterId === chapterId) void latestFlushRef.current.flush("leave_chapter");
    };
  }, [activeId]);

  useEffect(() => {
    const guardUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", guardUnload);
    return () => window.removeEventListener("beforeunload", guardUnload);
  }, [dirty]);

  useEffect(() => {
    if (!isTauri() || !dirty) return;
    let unlisten: (() => void) | undefined;
    void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
      const appWindow = getCurrentWindow();
      void appWindow.onCloseRequested(async (event) => {
        if (allowCloseRef.current) return;
        event.preventDefault();
        const saved = await latestFlushRef.current.flush("leave_chapter");
        if (saved) {
          allowCloseRef.current = true;
          await appWindow.destroy();
        }
      }).then((dispose) => { unlisten = dispose; });
    });
    return () => unlisten?.();
  }, [dirty]);

  useHotkeys("ctrl+s, meta+s", (event) => {
    event.preventDefault();
    void flushDraft("manual_snapshot");
  }, { enableOnFormTags: true, enableOnContentEditable: true }, [api, activeId, doc, dirty, seq, copyQuery.data, chapters, workId]);
  useHotkeys("ctrl+shift+f, meta+shift+f", (event) => {
    event.preventDefault();
    setFocus((value) => !value);
  }, { enableOnFormTags: true, enableOnContentEditable: true });
  useHotkeys("escape", () => setFocus(false), { enabled: focus });
  useHotkeys("ctrl+b, meta+b", (event) => { event.preventDefault(); setPanelOpen((open) => !open); }, { enableOnFormTags: true, enableOnContentEditable: true });
  useHotkeys("ctrl+alt+b, meta+alt+b", (event) => { event.preventDefault(); setTreeOpen((open) => !open); }, { enableOnFormTags: true, enableOnContentEditable: true });

  useEffect(() => {
    if (!savedAt || !activeId || !api) return;
    const timer = window.setTimeout(() => void flushDraft("idle"), 120_000);
    return () => window.clearTimeout(timer);
  }, [activeId, api, savedAt]);

  useEffect(() => {
    if (copyQuery.data) {
      if (copyQuery.data.client_session_id === sessionId) return;
      setDoc(copyQuery.data.doc_json);
      latestDocRef.current = copyQuery.data.doc_json;
      setDirty(copyQuery.data.has_changes);
      setSeq(copyQuery.data.client_seq);
    }
  }, [copyQuery.data]);

  useEffect(() => {
    const worker = new Worker(new URL("../workers/diff.worker.ts", import.meta.url), { type: "module" });
    diffWorkerRef.current = worker;
    return () => { worker.terminate(); diffWorkerRef.current = null; };
  }, []);

  function calculateDiff(before: string, after: string) {
    const worker = diffWorkerRef.current;
    if (!worker) return Promise.resolve(diffVietnameseWords(before, after));
    const id = ++diffRequestRef.current;
    return new Promise<ReturnType<typeof diffVietnameseWords>>((resolve, reject) => {
      let timeout = 0;
      const onMessage = (event: MessageEvent<{ id: number; parts: ReturnType<typeof diffVietnameseWords> }>) => {
        if (event.data.id !== id) return;
        window.clearTimeout(timeout);
        worker.removeEventListener("message", onMessage);
        resolve(event.data.parts);
      };
      timeout = window.setTimeout(() => { worker.removeEventListener("message", onMessage); reject(new Error("diff_timeout")); }, 10_000);
      worker.addEventListener("message", onMessage);
      worker.postMessage({ id, before, after });
    });
  }

  useEffect(() => {
    if (!dirty || !doc || !api || !activeId || conflict || saveBlocked) return;
    let compositionTimer = 0;
    let waitedForComposition = 0;
    const saveWhenReady = () => {
      if (editorRef.current?.view.composing && waitedForComposition < 1_000) {
        waitedForComposition += 100;
        compositionTimer = window.setTimeout(saveWhenReady, 100);
        return;
      }
      const nextSeq = seq + 1;
      const savingDoc = doc;
      if (saveInFlightRef.current) return;
      saveInFlightRef.current = true;
      void saveWorkingCopyWithRetry(() => api.put<Copy>(`/v1/chapters/${activeId}/working-copy`, {
        doc_json: savingDoc,
        base_revision_id: copyQuery.data?.base_revision_id ?? chapters.find((chapter) => chapter.id === activeId)?.current_revision_id ?? null,
        client_session_id: sessionId,
        client_seq: nextSeq,
      })).then((saved) => {
        setSeq(nextSeq); setDirty(JSON.stringify(latestDocRef.current) !== JSON.stringify(savingDoc)); setSavedAt(new Date().toLocaleTimeString());
        queryClient.setQueryData(["working-copy", activeId], saved);
      }).catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 409) { setConflict(true); toast.error("Chương vừa có bản mới. Bản nháp của bạn vẫn còn trong cửa sổ này."); }
        else if (error instanceof ApiError && error.status === 423) { setSaveBlocked(true); toast.error("Chương đang khóa để làm nền cho AI. Nội dung vẫn còn trong cửa sổ này."); void queryClient.invalidateQueries({ queryKey: ["chapter", activeId] }); }
        else toast.error("Chưa lưu được bản nháp. Nội dung hiện còn trong cửa sổ này.");
      }).finally(() => { saveInFlightRef.current = false; });
    };
    const timer = window.setTimeout(saveWhenReady, 750);
    return () => { window.clearTimeout(timer); window.clearTimeout(compositionTimer); };
  }, [activeId, api, chapters, conflict, copyQuery.data?.base_revision_id, dirty, doc, queryClient, saveBlocked, seq]);

  async function addChapter() {
    if (!api) return;
    try {
      const created = await api.post<Chapter>(`/v1/works/${workId}/chapters`, { title: "Chương mới" });
      await queryClient.invalidateQueries({ queryKey: ["chapters", workId] });
      setSelectedId(created.id); setDoc(EMPTY_DOC); setDirty(false);
    } catch { toast.error("Không thể tạo chương"); }
  }

  async function requestPauseToEdit() {
    if (!api || !activeChapterQuery.data) return;
    setPausingForEdit(true);
    try {
      await api.post(`/v1/works/${workId}/autowrite/pause`, { reason: "edit_base", chapter_id: activeId });
      setPauseRequested(true);
      toast.success("Đã yêu cầu tạm dừng sau bước hiện tại");
    } catch { toast.error("Không thể yêu cầu tạm dừng tác vụ viết"); }
    finally { setPausingForEdit(false); }
  }

  async function keepMyCopy() {
    if (!api || !activeId || !doc) return;
    try {
      const latest = activeChapterQuery.data?.current_revision_id ?? null;
      const nextSeq = seq + 1;
      await api.put(`/v1/chapters/${activeId}/working-copy`, { doc_json: doc, base_revision_id: latest, client_session_id: sessionId, client_seq: nextSeq });
      setSeq(nextSeq); setDirty(false); setConflict(false); setSaveBlocked(false);
      await queryClient.invalidateQueries({ queryKey: ["working-copy", activeId] });
      toast.success("Đã giữ bản của bạn trên nền phiên bản mới");
    } catch { toast.error("Chưa thể giữ bản nháp; hãy so sánh hoặc tải bản mới"); }
  }

  async function loadServerCopy() {
    if (!activeId) return;
    await queryClient.invalidateQueries({ queryKey: ["working-copy", activeId], refetchType: "all" });
    setConflict(false); setSaveBlocked(false); setDoc(null); setDirty(false);
  }

  async function reorderChapter(dragId: string, targetId: string) {
    if (!api || dragId === targetId) return;
    const order = chapters.map((chapter) => chapter.id);
    const from = order.indexOf(dragId);
    const to = order.indexOf(targetId);
    if (from < 0 || to < 0) return;
    order.splice(from, 1);
    order.splice(to, 0, dragId);
    try {
      await api.post(`/v1/works/${workId}/chapters/reorder`, { chapter_ids: order });
      await queryClient.invalidateQueries({ queryKey: ["chapters", workId] });
    } catch { toast.error("Không thể sắp xếp chương khi truyện đang chạy"); }
  }

  function startResize(side: "left" | "right", event: React.PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const initial = side === "left" ? leftWidth : rightWidth;
    const move = (pointer: PointerEvent) => {
      const delta = pointer.clientX - startX;
      if (side === "left") setLeftWidth(Math.min(400, Math.max(180, initial + delta)));
      else setRightWidth(Math.min(520, Math.max(260, initial - delta)));
    };
    const stop = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", stop); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
  }

  function resizeWithKeyboard(side: "left" | "right", event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 16 : -16;
    if (side === "left") setLeftWidth((width) => Math.min(400, Math.max(180, width + delta)));
    else setRightWidth((width) => Math.min(520, Math.max(260, width - delta)));
  }

  if (!chapters.length && !chaptersQuery.isPending) return <section className="mx-auto max-w-4xl p-8"><EmptyState title="Truyện chưa có chương" description="Tạo chương đầu tiên để bắt đầu soạn thảo." action={<Button onClick={() => void addChapter()}><BookPlus className="size-4"/>Tạo chương</Button>} /></section>;

  return <section className={`flex h-full min-h-[34rem] flex-col ${focus ? "fixed inset-0 z-30 bg-stone-50" : ""}`}>
    <header className="flex min-h-12 items-center justify-between gap-3 border-b border-stone-200 bg-white px-4"><div className="flex min-w-0 items-center gap-2"><span className="truncate text-sm font-medium">{chapters.find((chapter) => chapter.id === activeId)?.title || "Không gian truyện"}</span><span className="shrink-0 text-xs text-stone-500">{chapters.find((chapter) => chapter.id === activeId)?.syllable_count ?? 0} âm tiết</span></div><nav aria-label="Chế độ không gian truyện" className="hidden items-center gap-1 md:flex">{(["outline", "write", "review", "bible"] as const).map((value) => <button key={value} onClick={() => setMode(value)} aria-current={mode === value ? "page" : undefined} className={`rounded px-2 py-1 text-xs ${mode === value ? "bg-stone-900 text-white" : "text-stone-500 hover:bg-stone-100"}`}>{({ outline: "Dàn ý", write: "Viết", review: "Review", bible: "Bible" })[value]}</button>)}</nav><div className="flex shrink-0 items-center gap-2"><span role="status" className="text-xs text-stone-500">{dirty ? "Đang chờ lưu…" : savedAt ? `Đã lưu ${savedAt}` : "Đã đồng bộ"}</span><Button variant="ghost" className="min-h-8" aria-label="Lưu phiên bản Ctrl+S" onClick={() => void flushDraft("manual_snapshot")}><Save className="size-4"/></Button><Button variant="ghost" aria-label={focus ? "Thoát chế độ tập trung" : "Chế độ tập trung"} onClick={() => setFocus(!focus)}><Focus className="size-4"/></Button><Button variant="ghost" aria-label={panelOpen ? "Thu gọn bảng bên" : "Mở bảng bên"} onClick={() => setPanelOpen(!panelOpen)}>{panelOpen ? <PanelRightClose className="size-4"/> : <PanelRightOpen className="size-4"/>}</Button></div></header>
    <div className="flex min-h-0 flex-1">
      {!focus && treeOpen && <aside style={{ width: leftWidth }} className="flex shrink-0 flex-col border-r border-stone-200 bg-white"><div className="flex items-center justify-between px-3 py-3"><h2 className="text-sm font-semibold">Chương</h2><Button variant="ghost" aria-label="Thêm chương" onClick={() => void addChapter()}><BookPlus className="size-4"/></Button></div><nav aria-label="Cây chương" className="min-h-0 flex-1 overflow-auto px-2 pb-3">{chapters.map((chapter) => <button key={chapter.id} type="button" draggable onDragStart={(event) => event.dataTransfer.setData("text/chapter-id", chapter.id)} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); void reorderChapter(event.dataTransfer.getData("text/chapter-id"), chapter.id); }} onClick={async () => { if (chapter.id !== activeId) await flushDraft("leave_chapter"); setSelectedId(chapter.id); setDoc(null); }} className={`mb-1 flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm ${chapter.id === activeId ? "bg-stone-900 text-white" : "hover:bg-stone-100"}`}><span className="truncate">Ch.{chapter.chapter_no} {chapter.title}</span><span className="text-xs opacity-70">{chapter.status} {chapter.revision_count ? `· v${chapter.revision_count}` : ""}</span></button>)}</nav></aside>}
      {!focus && treeOpen && <div role="separator" aria-label="Điều chỉnh độ rộng cây chương" aria-orientation="vertical" aria-valuemin={180} aria-valuemax={400} aria-valuenow={leftWidth} tabIndex={0} onPointerDown={(event) => startResize("left", event)} onKeyDown={(event) => resizeWithKeyboard("left", event)} className="w-1 shrink-0 cursor-col-resize bg-stone-200 hover:bg-emerald-600 focus-visible:bg-emerald-600" />}
      <div className="min-w-0 flex-1 overflow-auto bg-stone-50"><div className="mx-auto max-w-4xl"><div className="flex items-center justify-between px-6 pt-4 text-xs text-stone-500"><span>Chương {chapters.find((chapter) => chapter.id === activeId)?.chapter_no ?? "—"}</span><span className="flex items-center gap-1"><Save className="size-3"/>{dirty ? "Đang lưu tự động" : "Tự động lưu"}</span></div>{activeChapterQuery.data?.is_base_locked && <div role="status" className="mx-6 mt-3 flex items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"><span>{pauseRequested ? "Đang dừng sau bước hiện tại…" : "Chương này đang được dùng làm nền cho một tác vụ AI nên đang ở chế độ chỉ đọc."}</span><Button variant="secondary" className="min-h-8 shrink-0" disabled={pausingForEdit || pauseRequested} onClick={() => void requestPauseToEdit()}>{pausingForEdit ? "Đang yêu cầu…" : "Tạm dừng để sửa"}</Button></div>}{conflict && <div role="alert" className="mx-6 mt-3 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-950"><p className="font-medium">Chương vừa có bản mới. Thay đổi của bạn vẫn còn trong cửa sổ này.</p><div className="mt-2 flex gap-2"><Button variant="secondary" className="min-h-8" onClick={() => setTab("history")}>So sánh</Button><Button variant="secondary" className="min-h-8" onClick={() => void keepMyCopy()}>Giữ bản của tôi</Button><Button variant="secondary" className="min-h-8" onClick={() => void loadServerCopy()}>Lấy bản mới</Button></div></div>}<ChapterEditor onEditorReady={(editor) => { editorRef.current = editor; }} initialContent={initialDoc} editable={!activeChapterQuery.data?.is_base_locked} onChange={(next) => { latestDocRef.current = next; setDoc(next); setDirty(true); }} /></div></div>
      {!focus && panelOpen && <><div role="separator" aria-label="Điều chỉnh độ rộng bảng bên" aria-orientation="vertical" aria-valuemin={260} aria-valuemax={520} aria-valuenow={rightWidth} tabIndex={0} onPointerDown={(event) => startResize("right", event)} onKeyDown={(event) => resizeWithKeyboard("right", event)} className="w-1 shrink-0 cursor-col-resize bg-stone-200 hover:bg-emerald-600 focus-visible:bg-emerald-600"/><aside style={{ width: rightWidth }} className="shrink-0 border-l border-stone-200 bg-white"><div className="flex flex-wrap gap-1 border-b border-stone-200 p-2">{(["ai", "characters", "memory", "handoff", "review", "history"] as const).map((name) => <button key={name} onClick={() => setTab(name)} className={`rounded px-2 py-1 text-xs ${tab === name ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"}`}>{({ ai: "AI", characters: "Nhân vật", memory: "Nhớ", handoff: "Nối", review: "Review", history: "Lịch sử" })[name]}</button>)}</div>
        <div className="p-4">
          {tab === "history" ? <>
            <h2 className="mb-3 flex items-center gap-2 font-semibold"><History className="size-4"/>Phiên bản</h2>
            {historyDiff && <div aria-label="So sánh theo từ với bản đang sửa" className="mb-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-stone-50 p-3 text-xs leading-6">
              {(historyDiff.parts ?? diffVietnameseWords(historyDiff.before, historyDiff.after)).map((part, index) => part.added
                ? <ins key={index} className="bg-emerald-100 text-emerald-950 no-underline">{part.value}</ins>
                : part.removed ? <del key={index} className="bg-red-100 text-red-900">{part.value}</del>
                : <span key={index}>{part.value}</span>)}
            </div>}
            {(revisionsQuery.data ?? []).map((revision) => <article key={revision.id} className="mb-2 rounded-lg border border-stone-200 p-3">
              <div className="flex justify-between text-sm font-medium"><span>Bản v{revision.revision_no}</span><span className="text-xs text-stone-500">{revision.source}</span></div>
              <p className="mt-1 text-xs text-stone-500">{revision.reason} · {new Date(revision.created_at).toLocaleString()}</p>
              <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs">{revision.plain_text}</p>
              <div className="mt-2 flex gap-2">
                <Button variant="secondary" className="min-h-8" onClick={async () => { try { const result = await api!.get<{ before: { plain_text: string }; after: { paragraphs: { text: string }[] } }>(`/v1/chapters/${activeId}/revisions/${revision.id}/diff/working`); const before = result.before.plain_text; const after = result.after.paragraphs.map((paragraph) => paragraph.text).join("\n\n"); setHistoryDiff({ before, after, parts: await calculateDiff(before, after) }); } catch { toast.error("Không thể tạo so sánh"); } }}>So sánh</Button>
              <Button variant="secondary" className="min-h-8" onClick={async () => { try { await api?.post(`/v1/chapters/${activeId}/revisions/${revision.id}/restore`, { expected_revision: activeChapterQuery.data?.revision_count ?? 0 }); await queryClient.invalidateQueries({ queryKey: ["working-copy", activeId] }); await queryClient.invalidateQueries({ queryKey: ["revisions", activeId] }); await queryClient.invalidateQueries({ queryKey: ["chapter", activeId] }); toast.success("Đã khôi phục thành phiên bản mới"); } catch { toast.error("Không thể khôi phục phiên bản"); } }}>Khôi phục</Button>
              </div>
            </article>)}
          </> : <><h2 className="font-semibold">{{ ai: "Viết cùng AI", characters: "Nhân vật", memory: "Ghi nhớ truyện", handoff: "Bản giao nối", review: "Review chương" }[tab]}</h2><p className="mt-2 text-sm text-stone-500">{tab === "ai" ? "Bản AI sẽ hiển thị riêng để bạn xem diff trước khi nhận." : "Thông tin liên quan sẽ được cung cấp khi hoàn thành các bước tiếp theo."}</p></>}
        </div>
      </aside></>}
    </div>
  </section>;
}
