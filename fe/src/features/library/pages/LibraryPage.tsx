import { useTranslation } from "react-i18next";

export function LibraryPage() {
  const { t } = useTranslation();
  return (
    <section className="mx-auto max-w-5xl p-6">
      <h1 className="mb-6 text-2xl font-semibold">{t("library.title")}</h1>
      <div className="rounded-lg border border-dashed border-stone-300 bg-white p-10 text-center">
        <p className="text-lg font-medium">{t("library.emptyTitle")}</p>
        <p className="mt-2 text-sm text-stone-500">{t("library.emptyHint")}</p>
      </div>
    </section>
  );
}
