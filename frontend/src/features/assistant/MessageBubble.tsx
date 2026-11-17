import { dateTime } from "../../shared/lib/format";
import Icon from "../../shared/ui/Icon";
import { sourceLabels } from "./model";
import type { ChatMessage } from "./types";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const assistant = message.role === "ASSISTANT";
  return (
    <article className={`chat-message ${assistant ? "from-assistant" : "from-user"}`}>
      <div className="chat-message-heading">
        <strong>{assistant ? "Trợ lý kho" : "Bạn"}</strong>
        <time dateTime={message.created_at}>{dateTime(message.created_at)}</time>
      </div>
      <p className="chat-message-content">{message.content}</p>
      {message.sources.length > 0 && (
        <ul className="chat-sources" aria-label="Nguồn dữ liệu">
          {message.sources.map((source, index) => (
            <li key={`${source.type}-${index}`}>
              <Icon name="check" size={14} />
              <span>
                {sourceLabels[source.type] ?? "Dữ liệu kho"}
                {source.sku ? ` · ${source.sku}` : ""}
                <small>{dateTime(source.as_of)} · giờ Việt Nam</small>
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
