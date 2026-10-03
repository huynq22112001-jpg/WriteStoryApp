import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useSearch } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { currentSession, createApiClient, newIdempotencyKey } from "@/shared/api/client";

const steps = ["Thông tin cơ bản", "Tóm tắt", "Nền truyện", "Quy tắc xưng hô", "Dàn ý sự kiện", "Cấu hình viết", "Xem lại"] as const;
const wizardStepNames = ["basics", "brief", "foundation", "address_rules", "event_outline", "writing_config", "review"] as const;
const wizardSchema = z.object({
  title: z.string().trim().min(1, "Hãy nhập tên truyện").max(200, "Tên truyện tối đa 200 ký tự"),
  brief: z.string().max(10000, "Tóm tắt tối đa 10.000 ký tự"),
  targetChapters: z.number().int().min(1),
  chapterMin: z.number().int().min(1),
  chapterMax: z.number().int().min(1),
}).refine((value) => value.chapterMax >= value.chapterMin, { message: "Độ dài tối đa phải lớn hơn hoặc bằng tối thiểu", path: ["chapterMax"] });
type WizardValues = z.infer<typeof wizardSchema>;
type DraftWork = { id: string; revision: number; style_profile?: { revision: number } | null };
type ResumableWork = DraftWork & { title: string; genre: string | null; brief: string | null; target_chapters: number | null; chapter_length_min: number; chapter_length_max: number; autowrite_mode_default: string; wizard_step: string | null; style_profile?: { revision: number; vocab_register: "han_viet" | "balanced" | "thuan_viet"; dialogue_style: "dash" | "quotes"; tone_mark_style: "old" | "new" } | null };
type GenrePreset = { key: string; label: string; defaults: { vocab_register: "han_viet" | "balanced" | "thuan_viet"; dialogue_style: "dash" | "quotes"; tone_mark_style: "old" | "new"; chapter_length_min: number; chapter_length_max: number } };

export function NewWorkPage() {
  const { register, watch, setValue, trigger, formState: { errors } } = useForm<WizardValues>({
    resolver: zodResolver(wizardSchema),
    mode: "onSubmit",
    defaultValues: { title: "", brief: "", targetChapters: 20, chapterMin: 1500, chapterMax: 2500 },
  });
  const title = watch("title");
  const [genre, setGenre] = useState("");
  const brief = watch("brief");
  const targetChapters = watch("targetChapters");
  const chapterMin = watch("chapterMin");
  const chapterMax = watch("chapterMax");
  const [mode, setMode] = useState("review_each");
  const [vocabRegister, setVocabRegister] = useState<"han_viet" | "balanced" | "thuan_viet">("balanced");
  const [dialogueStyle, setDialogueStyle] = useState<"dash" | "quotes">("dash");
  const [toneMarkStyle, setToneMarkStyle] = useState<"old" | "new">("new");
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<DraftWork | null>(null);
  const navigate = useNavigate();
  const search = useSearch({ from: "/new" });
  const session = currentSession();
  const api = session ? createApiClient(session) : null;
  const genresQuery = useQuery({ queryKey: ["genres", "vi"], enabled: !!api, queryFn: () => api!.get<GenrePreset[]>("/v1/languages/vi/genres") });
  const resumeQuery = useQuery({ queryKey: ["wizard-work", search.workId], enabled: !!api && !!search.workId, queryFn: () => api!.get<ResumableWork>(`/v1/works/${search.workId}`) });

  useEffect(() => {
    const work = resumeQuery.data;
    if (!work) return;
    setValue("title", work.title); setGenre(work.genre ?? ""); setValue("brief", work.brief ?? ""); setValue("targetChapters", work.target_chapters ?? 20);
    setValue("chapterMin", work.chapter_length_min); setValue("chapterMax", work.chapter_length_max); setMode(work.autowrite_mode_default);
    setDraft(work);
    setVocabRegister(work.style_profile?.vocab_register ?? "balanced");
    setDialogueStyle(work.style_profile?.dialogue_style ?? "dash");
    setToneMarkStyle(work.style_profile?.tone_mark_style ?? "new");
    const index = wizardStepNames.indexOf((search.step ?? work.wizard_step ?? "basics") as typeof wizardStepNames[number]);
    setStep(index >= 0 ? index : 0);
  }, [resumeQuery.data]);

  function selectGenre(nextGenre: string) {
    setGenre(nextGenre);
    const defaults = genresQuery.data?.find((preset) => preset.key === nextGenre)?.defaults;
    if (!defaults) return;
    setVocabRegister(defaults.vocab_register);
    setDialogueStyle(defaults.dialogue_style);
    setToneMarkStyle(defaults.tone_mark_style);
    setValue("chapterMin", defaults.chapter_length_min);
    setValue("chapterMax", defaults.chapter_length_max);
  }

  async function saveStyleProfile(workId: string, expectedRevision: number) {
    if (!api) return null;
    return api.put<{ revision: number }>(`/v1/works/${workId}/style-profile`, {
      expected_revision: expectedRevision,
      vocab_register: vocabRegister,
      dialogue_style: dialogueStyle,
      dialogue_dash_char: dialogueStyle === "dash" ? "–" : null,
      tone_mark_style: toneMarkStyle,
      punctuation_rules: {},
      banned_phrases: [],
      voice_samples: [],
    });
  }

  async function saveStep(nextStep: number) {
    const session = currentSession();
    if (!session || !api) { toast.error("Chưa kết nối backend"); return false; }
    try {
      if (!draft) {
        const work = await api.post<DraftWork>("/v1/works", { title: title.trim(), language: "vi", genre: genre || null, wizard_step: wizardStepNames[nextStep] ?? "review" }, { idempotencyKey: newIdempotencyKey() });
        let savedProfile: { revision: number } | null = null;
        try { savedProfile = await saveStyleProfile(work.id, work.style_profile?.revision ?? 1); } catch { toast.error("Đã tạo bản nháp nhưng chưa lưu được hồ sơ văn phong"); }
        const saved = await api.patch<DraftWork & { revision: number }>(`/v1/works/${work.id}`, { expected_revision: work.revision, wizard_step: wizardStepNames[nextStep], wizard_completed_steps: ["basics"] });
        setDraft({ ...saved, style_profile: savedProfile ?? work.style_profile });
        await navigate({ to: "/new", search: { workId: work.id, step: wizardStepNames[nextStep] ?? "review" } });
      } else {
        const patch: Record<string, unknown> = { expected_revision: draft.revision, wizard_step: wizardStepNames[nextStep], wizard_completed_steps: wizardStepNames.slice(0, step + 1) };
        if (step === 1) patch.brief = brief;
        if (step === 5) Object.assign(patch, { target_chapters: targetChapters, chapter_length_min: chapterMin, chapter_length_max: chapterMax, autowrite_mode_default: mode });
        const saved = await api.patch<DraftWork & { revision: number }>(`/v1/works/${draft.id}`, patch);
        setDraft(saved);
        await navigate({ to: "/new", search: { workId: draft.id, step: String(patch.wizard_step) } });
        try { const profile = await saveStyleProfile(draft.id, draft.style_profile?.revision ?? 1); if (profile) setDraft((current) => current ? { ...current, style_profile: profile } : current); } catch { toast.error("Chưa lưu được hồ sơ văn phong"); }
      }
      return true;
    } catch { toast.error("Không thể lưu bản nháp của bước này"); return false; }
  }

  async function advance() {
    if (step === 0 && !(await trigger("title"))) return;
    if (step === 1 && !(await trigger("brief"))) return;
    if (step === 5 && !(await trigger(["targetChapters", "chapterMin", "chapterMax"]))) return;
    if (step < steps.length - 1) {
      if (await saveStep(step + 1)) setStep((value) => value + 1);
      return;
    }
    if (!draft) return;
    try {
      const session = currentSession();
      if (session) await createApiClient(session).patch(`/v1/works/${draft.id}`, { expected_revision: draft.revision, wizard_step: null, status: "draft" });
      await navigate({ to: "/works/$workId", params: { workId: draft.id } });
    } catch { toast.error("Không thể hoàn tất tạo truyện"); }
  }

  return <section className="mx-auto max-w-3xl p-8"><p className="text-sm text-stone-500">Bước {step + 1} / {steps.length}</p><h1 className="mt-2 text-2xl font-semibold">Tạo truyện mới</h1><nav aria-label="Các bước tạo truyện" className="mt-5 grid grid-cols-4 gap-2 sm:grid-cols-7">{steps.map((label, index) => <button key={label} type="button" aria-current={index === step ? "step" : undefined} onClick={() => { if (index < step) setStep(index); }} className={`rounded-md border px-2 py-2 text-xs ${index === step ? "border-emerald-700 bg-emerald-50 font-medium" : "border-stone-200 text-stone-500"}`}>{index + 1}. {label}</button>)}</nav>
    <div className="mt-5 min-h-72 rounded-xl border border-stone-200 bg-white p-6">
      {step === 0 && <div className="grid max-w-xl gap-4"><div className="grid gap-2"><Label htmlFor="work-title">Tên truyện</Label><Input id="work-title" autoFocus maxLength={200} {...register("title")} />{errors.title && <p role="alert" className="text-sm text-red-700">{errors.title.message}</p>}</div><div className="grid gap-2"><Label htmlFor="work-genre">Thể loại</Label><select id="work-genre" className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm" value={genre} onChange={(event) => selectGenre(event.target.value)}><option value="">Chưa chọn</option>{(genresQuery.data ?? []).map((preset) => <option key={preset.key} value={preset.key}>{preset.label}</option>)}</select></div><fieldset className="grid gap-3 rounded-lg border border-stone-200 p-4"><legend className="px-1 text-sm font-medium">Hồ sơ văn phong</legend><div className="grid gap-2"><Label htmlFor="vocab-register">Vốn từ</Label><select id="vocab-register" value={vocabRegister} onChange={(event) => setVocabRegister(event.target.value as typeof vocabRegister)} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="han_viet">Hán Việt</option><option value="balanced">Cân bằng</option><option value="thuan_viet">Thuần Việt</option></select></div><div className="grid gap-2"><Label htmlFor="dialogue-style">Lời thoại</Label><select id="dialogue-style" value={dialogueStyle} onChange={(event) => setDialogueStyle(event.target.value as typeof dialogueStyle)} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="dash">Gạch đầu dòng</option><option value="quotes">Ngoặc kép</option></select></div><div className="grid gap-2"><Label htmlFor="tone-mark-style">Dấu thanh</Label><select id="tone-mark-style" value={toneMarkStyle} onChange={(event) => setToneMarkStyle(event.target.value as typeof toneMarkStyle)} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="new">Kiểu mới</option><option value="old">Kiểu cũ</option></select></div></fieldset></div>}
      {step === 1 && <div className="grid gap-2"><Label htmlFor="work-brief">Tóm tắt truyện</Label><textarea id="work-brief" {...register("brief")} className="min-h-48 rounded-md border border-stone-300 p-3 text-sm" placeholder="Nhân vật chính muốn gì? Điều gì cản trở họ?" />{errors.brief && <p role="alert" className="text-sm text-red-700">{errors.brief.message}</p>}</div>}
      {[2, 3, 4].includes(step) && <div className="rounded-lg bg-stone-50 p-5"><h2 className="font-semibold">{steps[step]}</h2><p className="mt-2 text-sm text-stone-600">Bước này sẽ được bổ sung trong phần Nền truyện. Bản nháp của bạn vẫn được lưu khi chuyển bước.</p></div>}
      {step === 5 && <div className="grid max-w-xl gap-4"><div className="grid gap-2"><Label htmlFor="target-chapters">Số chương mục tiêu</Label><Input id="target-chapters" type="number" min={1} {...register("targetChapters", { valueAsNumber: true })}/></div><div className="grid gap-2"><Label htmlFor="chapter-min">Độ dài tối thiểu (âm tiết)</Label><Input id="chapter-min" type="number" min={1} {...register("chapterMin", { valueAsNumber: true })}/></div><div className="grid gap-2"><Label htmlFor="chapter-max">Độ dài tối đa (âm tiết)</Label><Input id="chapter-max" type="number" min={chapterMin} {...register("chapterMax", { valueAsNumber: true })}/>{errors.chapterMax && <p role="alert" className="text-sm text-red-700">{errors.chapterMax.message}</p>}</div><div className="grid gap-2"><Label htmlFor="autowrite-mode">Chế độ viết mặc định</Label><select id="autowrite-mode" value={mode} onChange={(event) => setMode(event.target.value)} className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm"><option value="review_each">Duyệt từng chương</option><option value="review_every_k">Duyệt theo lô</option><option value="auto">Tự động</option></select></div></div>}
      {step === 6 && <div className="space-y-3"><h2 className="font-semibold">Kiểm tra thông tin truyện</h2><dl className="grid grid-cols-[10rem_1fr] gap-2 text-sm"><dt className="text-stone-500">Tên truyện</dt><dd>{title}</dd><dt className="text-stone-500">Thể loại</dt><dd>{genre || "Chưa chọn"}</dd><dt className="text-stone-500">Tóm tắt</dt><dd className="whitespace-pre-wrap">{brief || "Chưa nhập"}</dd><dt className="text-stone-500">Số chương mục tiêu</dt><dd>{targetChapters}</dd><dt className="text-stone-500">Độ dài chương</dt><dd>{chapterMin}–{chapterMax} âm tiết</dd><dt className="text-stone-500">Vốn từ</dt><dd>{vocabRegister}</dd><dt className="text-stone-500">Kiểu thoại</dt><dd>{dialogueStyle === "dash" ? "Gạch đầu dòng" : "Ngoặc kép"}</dd><dt className="text-stone-500">Dấu thanh</dt><dd>{toneMarkStyle === "new" ? "Kiểu mới" : "Kiểu cũ"}</dd></dl></div>}
    </div>
    <div className="mt-5 flex justify-between"><Button variant="secondary" onClick={() => { const previous = Math.max(0, step - 1); setStep(previous); if (draft) void navigate({ to: "/new", search: { workId: draft.id, step: wizardStepNames[previous] } }); }} disabled={step === 0}>Quay lại</Button><Button onClick={() => void advance()} disabled={step === 6 && !draft}>{step === 6 ? "Hoàn tất" : "Lưu và tiếp tục"}</Button></div>
  </section>;
}
