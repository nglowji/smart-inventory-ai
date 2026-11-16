export const formText = (data: FormData, key: string): string =>
  String(data.get(key) ?? "").trim();
export const optionalFormText = (data: FormData, key: string): string | null =>
  formText(data, key) || null;
