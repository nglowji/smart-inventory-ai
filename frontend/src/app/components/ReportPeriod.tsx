import type { FormEvent } from "react";
import { useState } from "react";
import type { Range } from "../../shared/contracts";
import { isValidRange, presetFor, rangeFor } from "../../shared/lib/dates";
import Icon from "../../shared/ui/Icon";

export default function ReportPeriod({
  range,
  onChange,
}: {
  range: Range;
  onChange: (range: Range) => void;
}) {
  const [draft, setDraft] = useState(range);
  const [preset, setPreset] = useState(() => presetFor(range));
  const [rangeError, setRangeError] = useState("");
  function applyDates(event: FormEvent) {
    event.preventDefault();
    if (!isValidRange(draft)) {
      setRangeError("Chọn khoảng ngày hợp lệ, tối đa 366 ngày.");
      return;
    }
    setRangeError("");
    onChange({ ...draft });
  }
  return (
    <>
      <form className="range-toolbar" onSubmit={applyDates}>
        <div className="range-description">
          <Icon name="activity" size={18} />
          <span>Kỳ báo cáo</span>
        </div>
        <select
          aria-label="Khoảng ngày nhanh"
          value={preset}
          onChange={(e) => {
            setPreset(e.target.value);
            if (e.target.value !== "custom") {
              const next = rangeFor(Number(e.target.value));
              onChange(next);
              setDraft(next);
              setRangeError("");
            }
          }}
        >
          <option value="7">7 ngày gần nhất</option>
          <option value="30">30 ngày gần nhất</option>
          <option value="90">90 ngày gần nhất</option>
          <option value="custom">Tùy chọn</option>
        </select>
        <div className="date-inputs">
          <label>
            <span className="sr-only">Từ ngày</span>
            <input
              type="date"
              required
              value={draft.date_from}
              onChange={(e) => {
                setDraft({ ...draft, date_from: e.target.value });
                setPreset("custom");
              }}
            />
          </label>
          <span>—</span>
          <label>
            <span className="sr-only">Đến ngày</span>
            <input
              type="date"
              required
              value={draft.date_to}
              onChange={(e) => {
                setDraft({ ...draft, date_to: e.target.value });
                setPreset("custom");
              }}
            />
          </label>
          <button className="button" type="submit">
            Áp dụng
          </button>
        </div>
        <span className="range-hint">Giờ Việt Nam (UTC+7)</span>
      </form>
      {rangeError && (
        <p className="error-banner" role="alert">
          {rangeError}
        </p>
      )}
    </>
  );
}
