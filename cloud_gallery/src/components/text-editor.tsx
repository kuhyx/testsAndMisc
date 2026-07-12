import { useEffect, useState } from "react";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";

interface TextEditorProps {
  readonly client: DufsClient;
  readonly entry: DirEntry;
  readonly onClose: () => void;
}

type Status = "loading" | "ready" | "saving" | "error";

/** A minimal editor for .txt/.md files: GET the text, edit, PUT it back. */
export function TextEditor({
  client,
  entry,
  onClose,
}: TextEditorProps): React.JSX.Element {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status>("loading");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    client
      .readText(entry.path)
      .then((content) => {
        if (cancelled) return;
        setText(content);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setMessage(err instanceof Error ? err.message : String(err));
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [client, entry.path]);

  function save(): void {
    setStatus("saving");
    setMessage(null);
    client
      .writeText(entry.path, text)
      .then(() => {
        setStatus("ready");
        setMessage("Saved");
      })
      .catch((err: unknown) => {
        setMessage(err instanceof Error ? err.message : String(err));
        setStatus("error");
      });
  }

  return (
    <div className="overlay" role="dialog" aria-modal="true">
      <div
        className="dialog editor"
        onClick={(e) => {
          e.stopPropagation();
        }}
      >
        <header className="editor-head">
          <span>{entry.name}</span>
          <span className="editor-status">{message ?? status}</span>
        </header>
        <textarea
          className="editor-area"
          value={text}
          spellCheck={false}
          disabled={status === "loading"}
          onChange={(e) => {
            setText(e.target.value);
          }}
        />
        <div className="dialog-actions">
          <button type="button" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="primary"
            disabled={status === "loading" || status === "saving"}
            onClick={save}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
