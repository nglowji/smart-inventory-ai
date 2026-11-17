import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { errorMessage } from "../../shared/api/errors";
import { useResource } from "../../shared/hooks/useResource";
import { Failure, Loading } from "../../shared/ui/Feedback";
import Icon from "../../shared/ui/Icon";
import { Pagination } from "../../shared/ui/Pagination";
import { fetchMessages, sendMessage } from "./api";
import MessageBubble from "./MessageBubble";
import type { AiStatus, Conversation } from "./types";

export default function ChatThread({
  conversation,
  initialDraft,
  status,
  version,
  changed,
  onBusyChange,
}: {
  conversation: Conversation;
  initialDraft: string;
  status: AiStatus | null;
  version: number;
  changed: () => void;
  onBusyChange: (busy: boolean) => void;
}) {
  const [draft, setDraft] = useState(initialDraft);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [pending, setPending] = useState("");
  const [localVersion, setLocalVersion] = useState(0);
  const request = useRef<{ message: string; id: string } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const timeline = useRef<HTMLDivElement>(null);
  const load = useCallback(
    (signal: AbortSignal) => fetchMessages(conversation.id, page, signal),
    [conversation.id, page],
  );
  const history = useResource(load, version + localVersion);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => {
    if (timeline.current && page === 1)
      timeline.current.scrollTop = timeline.current.scrollHeight;
  }, [history.data, pending, page]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || controller.current || !status?.available) return;
    if (request.current?.message !== message)
      request.current = { message, id: crypto.randomUUID() };
    const active = new AbortController();
    controller.current = active;
    setError("");
    setPending(message);
    onBusyChange(true);
    try {
      await sendMessage(conversation.id, message, request.current.id, active.signal);
      if (active.signal.aborted) return;
      setDraft("");
      request.current = null;
      setPage(1);
      setLocalVersion((v) => v + 1);
      changed();
    } catch (failure) {
      if (!active.signal.aborted) setError(errorMessage(failure));
    } finally {
      controller.current = null;
      setPending("");
      onBusyChange(false);
    }
  }
  return (
    <section className="panel chat-thread" aria-label="Nội dung trò chuyện">
      <header className="panel-heading">
        <div>
          <h2>{conversation.title}</h2>
          <p>Câu trả lời có nguồn và thời điểm tra cứu</p>
        </div>
        <span className="badge success">Chỉ đọc</span>
      </header>
      <div
        ref={timeline}
        className="chat-timeline"
        role="log"
        aria-label="Tin nhắn"
        aria-relevant="additions"
        aria-busy={Boolean(pending)}
      >
        {history.error ? (
          <Failure message={history.error} retry={() => setLocalVersion((v) => v + 1)} />
        ) : !history.data ? (
          <Loading />
        ) : (
          <>
            {history.data.total > 50 && (
              <fieldset disabled={Boolean(pending)} className="chat-history-pages">
                <Pagination
                  total={history.data.total}
                  page={page}
                  pageSize={50}
                  change={setPage}
                />
              </fieldset>
            )}
            {!history.data.items.length && (
              <div className="chat-thread-empty">
                <Icon name="chat" size={30} />
                <h3>Bạn muốn biết điều gì về kho?</h3>
                <p>Hỏi bằng mã SKU, tên sản phẩm hoặc khoảng ngày cần tra cứu.</p>
              </div>
            )}
            {history.data.items.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </>
        )}
        {pending && (
          <div className="chat-pending" role="status">
            <p className="chat-message-content">{pending}</p>
            <span>Đang tra cứu dữ liệu kho…</span>
          </div>
        )}
      </div>
      <form className="chat-composer" onSubmit={(e) => void submit(e)}>
        {error && (
          <div className="chat-error" role="alert">
            {error} Câu hỏi vẫn được giữ để bạn gửi lại.
          </div>
        )}
        {!status?.available && (
          <p className="chat-unavailable" role="status">
            {status?.message ?? "Đang kiểm tra kết nối AI…"}
          </p>
        )}
        <label htmlFor="chat-question" className="sr-only">
          Câu hỏi về kho
        </label>
        <textarea
          id="chat-question"
          ref={input}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ví dụ: Mã SKU này còn bao nhiêu?"
          rows={3}
          maxLength={2000}
          disabled={Boolean(pending) || !status?.available}
          required
        />
        <div className="chat-composer-footer">
          <span>{draft.length}/2000 · Gợi ý nhập hàng cần được bạn xem xét</span>
          <button
            type="submit"
            className="button primary"
            disabled={Boolean(pending) || !status?.available || !draft.trim()}
          >
            <Icon name="arrow" size={17} />
            {pending ? "Đang tra cứu…" : "Gửi câu hỏi"}
          </button>
        </div>
      </form>
    </section>
  );
}
