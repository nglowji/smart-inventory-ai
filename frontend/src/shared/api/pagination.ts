import type { Page } from "../contracts";
import { api } from "./client";

export const PAGE_SIZE = 10;

export async function allPages<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const items: T[] = [];
  let page = 1;
  while (true) {
    signal?.throwIfAborted();
    const result = await api<Page<T>>(
      `${path}${path.includes("?") ? "&" : "?"}page=${page}&page_size=100`,
      { signal },
    );
    items.push(...result.items);
    if (items.length >= result.total || !result.items.length) return items;
    page += 1;
  }
}
