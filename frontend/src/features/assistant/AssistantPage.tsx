import { useCallback, useState } from "react";
import { errorMessage } from "../../shared/api/errors";
import { useResource } from "../../shared/hooks/useResource";
import { dateTime } from "../../shared/lib/format";
import { Failure, Loading } from "../../shared/ui/Feedback";
import Icon from "../../shared/ui/Icon";
import { Pagination } from "../../shared/ui/Pagination";
import { createConversation, fetchAiStatus, fetchConversations } from "./api";
import ChatThread from "./ChatThread";
import { suggestions } from "./model";
import type { Conversation } from "./types";

export default function AssistantPage({ version }: { version: number }) {
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [selection, setSelection] = useState<{
    conversation: Conversation;
    draft: string;
  } | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(
    (signal: AbortSignal) => fetchConversations(page, signal),
    [page],
  );
  const status = useResource(fetchAiStatus, version + revision);
  const conversations = useResource(load, version + revision);
  const changed = useCallback(() => setRevision((v) => v + 1), []);
  async function create(question = "") {
    if (creating || busy || !status.data?.available) return;
    setCreating(true);
    setError("");
    try {
      const conversation = await createConversation(question.slice(0, 100) || undefined);
      setSelection({ conversation, draft: question });
      setPage(1);
      changed();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setCreating(false);
    }
  }
  return (
    <div className="assistant-layout">
      <aside className="panel conversation-sidebar" aria-label="Lịch sử trò chuyện">
        <header className="panel-heading">
          <div>
            <h2>Cuộc trò chuyện</h2>
            <p>Chỉ hiển thị lịch sử của bạn</p>
          </div>
        </header>
        <button
          className="button new-conversation"
          onClick={() => void create()}
          disabled={creating || busy || !status.data?.available}
        >
          <Icon name="plus" size={17} />
          {creating ? "Đang tạo…" : "Trò chuyện mới"}
        </button>
        {error && (
          <p className="chat-error" role="alert">
            {error}
          </p>
        )}
        {conversations.error ? (
          <Failure message={conversations.error} retry={changed} />
        ) : !conversations.data ? (
          <Loading />
        ) : (
          <>
            <div className="conversation-list">
              {conversations.data.items.map((conversation) => (
                <button
                  key={conversation.id}
                  disabled={busy || creating}
                  className={`conversation-item ${selection?.conversation.id === conversation.id ? "selected" : ""}`}
                  aria-current={
                    selection?.conversation.id === conversation.id ? "true" : undefined
                  }
                  onClick={() => setSelection({ conversation, draft: "" })}
                >
                  <strong>{conversation.title}</strong>
                  <time dateTime={conversation.updated_at}>
                    {dateTime(conversation.updated_at)}
                  </time>
                </button>
              ))}
              {!conversations.data.total && (
                <p className="conversation-empty">Chưa có cuộc trò chuyện nào.</p>
              )}
            </div>
            <fieldset disabled={busy || creating} className="chat-history-pages">
              <Pagination total={conversations.data.total} page={page} change={setPage} />
            </fieldset>
          </>
        )}
      </aside>
      <div className="assistant-main">
        {status.error && (
          <Failure message={status.error} retry={() => setRevision((v) => v + 1)} />
        )}
        {status.data?.mode === "mock" && (
          <p className="chat-mode" role="status">
            Chế độ kiểm thử: nhận diện câu hỏi bằng quy tắc, truy vấn dữ liệu kho thật.
          </p>
        )}
        {selection ? (
          <ChatThread
            key={selection.conversation.id}
            conversation={
              conversations.data?.items.find(
                (item) => item.id === selection.conversation.id,
              ) ?? selection.conversation
            }
            initialDraft={selection.draft}
            status={status.data}
            version={version}
            changed={changed}
            onBusyChange={setBusy}
          />
        ) : (
          <section className="panel assistant-welcome">
            <span className="assistant-symbol">
              <Icon name="chat" size={30} />
            </span>
            <span className="eyebrow">TRỢ LÝ KHO HÀNG</span>
            <h2>
              Hiểu dữ liệu kho,
              <br />
              ra quyết định rõ ràng hơn.
            </h2>
            <p>
              Tra cứu tồn, theo dõi xuất hàng và xem gợi ý nhập hàng. Mỗi kết quả kèm
              nguồn và thời điểm lấy dữ liệu.
            </p>
            {!status.data ? (
              status.error ? null : (
                <Loading />
              )
            ) : !status.data.available ? (
              <div className="assistant-connection" role="status">
                <Icon name="alert" size={20} />
                <div>
                  <strong>Chưa kết nối dịch vụ AI</strong>
                  <p>{status.data.message}</p>
                  <small>
                    Các chức năng sản phẩm, giao dịch và dashboard vẫn dùng bình thường.
                  </small>
                </div>
              </div>
            ) : (
              <div className="assistant-suggestions">
                {suggestions.map((question) => (
                  <button
                    className="assistant-suggestion"
                    key={question}
                    disabled={creating}
                    onClick={() => void create(question)}
                  >
                    <span>{question}</span>
                    <Icon name="arrow" size={16} />
                  </button>
                ))}
              </div>
            )}
            <span className="assistant-readonly">
              <Icon name="audit" size={16} /> Chỉ tra cứu · Không thay đổi tồn kho
            </span>
          </section>
        )}
      </div>
    </div>
  );
}
