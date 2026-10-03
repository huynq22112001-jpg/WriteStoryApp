import { useTranslation } from "react-i18next";

export function PagePlaceholder({ titleKey, hintKey }: { titleKey: string; hintKey?: string }) {
  const { t } = useTranslation();
  return <section className="mx-auto max-w-6xl p-8"><h1 className="text-2xl font-semibold">{t(titleKey)}</h1>{hintKey && <p className="mt-2 text-sm text-stone-500">{t(hintKey)}</p>}</section>;
}
