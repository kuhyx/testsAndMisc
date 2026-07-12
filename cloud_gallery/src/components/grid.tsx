import { useState } from "react";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";
import { humanSize, isImage, isText, isVideo } from "../lib/paths.ts";

interface GridProps {
  readonly client: DufsClient;
  readonly entries: readonly DirEntry[];
  readonly onOpenDir: (path: string) => void;
  readonly onOpenMedia: (entry: DirEntry) => void;
  readonly onEditText: (entry: DirEntry) => void;
  readonly onDelete: (entry: DirEntry) => void;
}

function Thumb({
  client,
  entry,
}: {
  readonly client: DufsClient;
  readonly entry: DirEntry;
}): React.JSX.Element {
  const [broken, setBroken] = useState(false);
  if (broken) {
    return <div className="thumb-fallback">{isVideo(entry.name) ? "🎞" : "🖼"}</div>;
  }
  return (
    <img
      className="thumb-img"
      src={client.thumbUrl(entry.path)}
      alt={entry.name}
      loading="lazy"
      onError={() => {
        setBroken(true);
      }}
    />
  );
}

export function Grid({
  client,
  entries,
  onOpenDir,
  onOpenMedia,
  onEditText,
  onDelete,
}: GridProps): React.JSX.Element {
  return (
    <ul className="grid">
      {entries.map((entry) => {
        const media = isImage(entry.name) || isVideo(entry.name);
        const activate = (): void => {
          if (entry.kind === "dir") onOpenDir(entry.path);
          else if (media) onOpenMedia(entry);
          else if (isText(entry.name)) onEditText(entry);
        };
        return (
          <li key={entry.path} className={`tile tile-${entry.kind}`}>
            <button type="button" className="tile-main" onClick={activate}>
              <span className="tile-preview">
                {entry.kind === "dir" ? (
                  <span className="tile-icon">📁</span>
                ) : media ? (
                  <>
                    <Thumb client={client} entry={entry} />
                    {isVideo(entry.name) && <span className="play-badge">▶</span>}
                  </>
                ) : (
                  <span className="tile-icon">{isText(entry.name) ? "📝" : "📄"}</span>
                )}
              </span>
              <span className="tile-name" title={entry.name}>
                {entry.name}
              </span>
              {entry.kind === "file" && (
                <span className="tile-size">{humanSize(entry.size)}</span>
              )}
            </button>
            {entry.kind === "file" && (
              <div className="tile-actions">
                <a
                  className="tile-act"
                  href={client.fileUrl(entry.path)}
                  download
                  aria-label={`Download ${entry.name}`}
                >
                  ⭳
                </a>
                <button
                  type="button"
                  className="tile-act danger"
                  aria-label={`Delete ${entry.name}`}
                  onClick={() => {
                    onDelete(entry);
                  }}
                >
                  🗑
                </button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
