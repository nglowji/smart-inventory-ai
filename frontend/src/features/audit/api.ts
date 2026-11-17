import { api } from "../../shared/api/client";
import { PAGE_SIZE } from "../../shared/api/pagination";
import { query } from "../../shared/api/query";
import type { AuditEntry, AuditEvent, Page, Range } from "../../shared/contracts";

export const fetchAudit = (
  range: Range,
  page: number,
  event: AuditEvent | "",
  signal: AbortSignal,
) =>
  api<Page<AuditEntry>>(
    `/audit?${query({ ...range, page, page_size: PAGE_SIZE, event_type: event })}`,
    { signal },
  );
