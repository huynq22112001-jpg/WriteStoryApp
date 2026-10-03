import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { BookOpen, Plus, Search } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { toast } from "sonner";
import { currentSession, createApiClient, newIdempotencyKey } from "@/shared/api/client";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Work = { id: string; title: string; genre: string | null; status: string; continuity_status: string; committed_chapters: number; target_chapters: number | null; badge: { label_key: string }; updated_at: string };
type WorkPage = { items: Work[]; next_cursor: string | null };

export function LibraryPage() {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const [title, setTitle] = useState("");
  const [genreFilter, setGenreFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const virtualListRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const session = currentSession();
  const worksQuery = useQuery({ queryKey: ["works", q], enabled: !!session, queryFn: () => createApiClient(session!).get<WorkPage>(`/v1/works?limit=100${q ? `&q=${encodeURIComponent(q)}` : ""}`) });
  const works = useMemo(() => worksQuery.data?.items ?? [], [worksQuery.data]);
  const filteredWorks = useMemo(() => works.filter((work) => (!genreFilter || work.genre === genreFilter) && (!statusFilter || work.status === statusFilter)), [genreFilter, statusFilter, works]);
  const virtualRows = useVirtualizer({ count: filteredWorks.length, getScrollElement: () => virtualListRef.current, estimateSize: () => 78, overscan: 6 });
  async function createWork() {
    if (!session || !title.trim()) return;
    try {
      const work = await createApiClient(session).post<Work>("/v1/works", { title: title.trim(), language: "vi" }, { idempotencyKey: newIdempotencyKey() });
      await queryClient.invalidateQueries({ queryKey: ["works"] });
      setTitle("");
      toast.success("Đã tạo truyện mới");
      window.location.hash = `#/works/${work.id}`;
    } catch { toast.error("Không thể tạo truyện"); }
  }
  return (
    <section className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-2xl font-semibold">{t("library.title")}</h1><p className="mt-1 text-sm text-stone-500">Quản lý tác phẩm và tiếp tục viết.</p></div>
        <Dialog trigger={<Button><Plus className="size-4"/>Tạo truyện</Button>} title="Tạo truyện mới" description="Bạn có thể bổ sung nền truyện và dàn ý sau."><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void createWork(); }}><div className="space-y-2"><Label htmlFor="new-work-title">Tên truyện</Label><Input id="new-work-title" autoFocus value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required /></div><Button type="submit" className="w-full">Tạo truyện</Button></form></Dialog>
      </div>
      <div className="relative mb-5 max-w-md"><Search className="absolute left-3 top-2.5 size-4 text-stone-400"/><Input aria-label="Tìm truyện" className="pl-9" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Tìm theo tiêu đề…" /></div>
      <div className="mb-5 flex flex-wrap gap-3"><select aria-label="Lọc thể loại" value={genreFilter} onChange={(event) => setGenreFilter(event.target.value)} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="">Mọi thể loại</option>{Array.from(new Set(works.map((work) => work.genre).filter((genre): genre is string => !!genre))).sort().map((genre) => <option key={genre} value={genre}>{genre}</option>)}</select><select aria-label="Lọc trạng thái" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="">Mọi trạng thái</option><option value="draft">Bản nháp</option><option value="ready">Sẵn sàng</option><option value="archived">Lưu trữ</option></select><div role="group" aria-label="Kiểu hiển thị" className="ml-auto flex gap-1"><Button variant={viewMode === "grid" ? "secondary" : "ghost"} className="min-h-8" onClick={() => setViewMode("grid")}>Lưới</Button><Button variant={viewMode === "list" ? "secondary" : "ghost"} className="min-h-8" onClick={() => setViewMode("list")}>Danh sách</Button></div></div>
      {worksQuery.isError && <ErrorState title="Không tải được thư viện" description="Kiểm tra kết nối backend rồi thử lại." onRetry={() => void worksQuery.refetch()} />}
      {worksQuery.isPending && !!session && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[0,1,2].map((i) => <div key={i} className="h-36 animate-pulse rounded-xl bg-stone-200" />)}</div>}
      {(!session || !worksQuery.isPending) && !worksQuery.isError && works.length === 0 && <EmptyState title={t("library.emptyTitle")} description={t("library.emptyHint")} action={<Dialog trigger={<Button><Plus className="size-4"/>Tạo truyện đầu tiên</Button>} title="Tạo truyện mới"><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void createWork(); }}><div className="space-y-2"><Label htmlFor="first-work-title">Tên truyện</Label><Input id="first-work-title" value={title} onChange={(event) => setTitle(event.target.value)} required /></div><Button type="submit">Tạo truyện</Button></form></Dialog>} />}
      {works.length > 0 && filteredWorks.length === 0 && <p className="rounded-lg border border-dashed border-stone-300 p-8 text-center text-sm text-stone-500">Không có truyện khớp bộ lọc.</p>}
      {viewMode === "list" && filteredWorks.length > 0 && <div ref={virtualListRef} className="max-h-[65vh] overflow-auto rounded-xl border border-stone-200 bg-white" role="list" aria-label="Danh sách truyện"><div style={{ height: virtualRows.getTotalSize(), position: "relative" }}>{virtualRows.getVirtualItems().map((virtualRow) => { const work = filteredWorks[virtualRow.index]!; return <Link key={work.id} to="/works/$workId" params={{ workId: work.id }} role="listitem" style={{ position: "absolute", top: 0, left: 0, width: "100%", height: virtualRow.size, transform: `translateY(${virtualRow.start}px)` }} className="flex items-center justify-between border-b border-stone-100 px-4 py-3 hover:bg-stone-50"><span className="min-w-0"><strong className="block truncate text-sm">{work.title}</strong><span className="text-xs text-stone-500">{work.genre ?? "Chưa chọn thể loại"} · {work.committed_chapters}{work.target_chapters ? `/${work.target_chapters}` : ""} chương</span></span><span className="ml-4 shrink-0 rounded-full bg-stone-100 px-2 py-1 text-xs">{t(work.badge.label_key)}</span></Link>; })}</div></div>}
      {filteredWorks.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{filteredWorks.map((work) => <Link key={work.id} to="/works/$workId" params={{ workId: work.id }} className="group rounded-xl border border-stone-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-emerald-700/40 hover:shadow-md"><div className="flex items-start justify-between"><BookOpen className="size-5 text-emerald-700"/><span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">{t(work.badge.label_key)}</span></div><h2 className="mt-5 truncate font-semibold group-hover:text-emerald-800">{work.title}</h2><p className="mt-1 text-sm text-stone-500">{work.genre ?? "Chưa chọn thể loại"} · {work.committed_chapters}{work.target_chapters ? `/${work.target_chapters}` : ""} chương</p></Link>)}</div>}
    </section>
  );
}
