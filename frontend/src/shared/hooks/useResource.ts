import { useEffect, useState } from "react";
import { errorMessage } from "../api/errors";

type Resource<T> =
  | { status: "loading"; data: null; error: "" }
  | { status: "success"; data: T; error: "" }
  | { status: "error"; data: null; error: string };

export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  version = 0,
): Resource<T> {
  const [state, setState] = useState<Resource<T>>({
    status: "loading",
    data: null,
    error: "",
  });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: "" });
    void load(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ status: "success", data, error: "" });
      },
      (error) => {
        if (!controller.signal.aborted)
          setState({ status: "error", data: null, error: errorMessage(error) });
      },
    );
    return () => controller.abort();
  }, [load, version]);
  return state;
}
