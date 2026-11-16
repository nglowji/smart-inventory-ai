import type { FormEvent, ReactNode } from "react";
import { useEffect, useId, useRef, useState } from "react";
import { errorMessage } from "../api/errors";
import Icon from "./Icon";

type Props = {
  title: string;
  children: ReactNode;
  submitLabel?: string;
  successMessage?: string;
  danger?: boolean;
  ready?: boolean;
  loadError?: string;
  close: () => void;
  saved: (message: string) => void;
  submit: (data: FormData) => Promise<void>;
};

export default function FormModal({
  title,
  children,
  submitLabel = "Lưu thay đổi",
  successMessage = "Đã lưu thay đổi thành công.",
  danger = false,
  ready = true,
  loadError = "",
  close,
  saved,
  submit,
}: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError("");
    setBusy(true);
    try {
      await submit(data);
      saved(successMessage);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      className="modal"
      ref={dialogRef}
      aria-labelledby={titleId}
      onCancel={(event) => {
        if (busy) event.preventDefault();
        else close();
      }}
    >
      <header className="modal-header">
        <div>
          <span className="eyebrow">KHO CHÍNH</span>
          <h2 id={titleId}>{title}</h2>
        </div>
        <button className="icon-button" onClick={close} disabled={busy} aria-label="Đóng">
          <Icon name="close" />
        </button>
      </header>
      <form onSubmit={onSubmit}>
        <fieldset disabled={busy || !ready} className="form-fields">
          {children}
        </fieldset>
        {!ready && !loadError && (
          <p role="status" className="muted">
            Đang tải thông tin…
          </p>
        )}
        {(error || loadError) && (
          <p className="error-banner" role="alert">
            {error || loadError}
          </p>
        )}
        <footer className="modal-footer">
          <button className="button" type="button" onClick={close} disabled={busy}>
            Hủy
          </button>
          <button
            className={`button ${danger ? "danger" : "primary"}`}
            disabled={busy || !ready}
          >
            {busy ? "Đang lưu…" : submitLabel}
          </button>
        </footer>
      </form>
    </dialog>
  );
}
