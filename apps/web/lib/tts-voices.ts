export const KDT_TTS_VOICES = [
  { value: "康迪", label: "康迪" },
  { value: "日标住建-小唐", label: "日标住建-小唐" },
  { value: "日标住建-凯迪", label: "日标住建-凯迪" },
] as const;

export const RIBIAO_EXCLUSIVE_TTS_VOICES = [
  { value: "日标住建-康迪2", label: "日标住建-康迪2" },
  { value: "日标住建-小唐2", label: "日标住建-小唐2" },
] as const;

export const RIBIAO_COMPANY_NAME = "日标住建";

export type KdtTtsVoiceName =
  | (typeof KDT_TTS_VOICES)[number]["value"]
  | (typeof RIBIAO_EXCLUSIVE_TTS_VOICES)[number]["value"];

export function getTtsVoicesForCompany(companyName?: string | null) {
  if (companyName === RIBIAO_COMPANY_NAME) {
    return [...KDT_TTS_VOICES, ...RIBIAO_EXCLUSIVE_TTS_VOICES] as const;
  }
  return KDT_TTS_VOICES;
}
