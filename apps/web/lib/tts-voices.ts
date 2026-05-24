export const KDT_TTS_VOICES = [
  { value: "康迪", label: "康迪" },
  { value: "日标住建-小唐", label: "日标住建-小唐" },
  { value: "日标住建-凯迪", label: "日标住建-凯迪" },
] as const;

export type KdtTtsVoiceName = (typeof KDT_TTS_VOICES)[number]["value"];
