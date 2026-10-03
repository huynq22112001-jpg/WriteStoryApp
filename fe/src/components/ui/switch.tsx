import { Switch as BaseSwitch } from "@base-ui/react/switch";

export function Switch(props: BaseSwitch.Root.Props) {
  return <BaseSwitch.Root {...props} className="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full bg-stone-300 p-0.5 outline-none transition data-[checked]:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-600">
    <BaseSwitch.Thumb className="block size-5 rounded-full bg-white shadow transition-transform data-[checked]:translate-x-5" />
  </BaseSwitch.Root>;
}
