export type QueryValues = Record<string, string | number | boolean | undefined>;

export function query(values: QueryValues): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return params.toString();
}
