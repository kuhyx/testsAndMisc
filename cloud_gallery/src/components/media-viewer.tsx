import { useEffect, useState } from "react";
import type { DirEntry } from "../api/types.ts";
import { isImage, isVideo } from "../lib/paths.ts";

interface MediaViewerProps {
  readonly entry: DirEntry;
  readonly url: string;
  readonly onClose: () => void;
  readonly onPrev: () => void;
  readonly onNext: () => void;
}

/** Full-screen viewer: image lightbox (click-to-zoom) or an inline video player. */
export function MediaViewer({
  entry,
  url,
  onClose,
  onPrev,
  onNext,
}: MediaViewerProps): React.JSX.Element {
  // Zoom resets automatically per media because the parent keys this component
  // by path, remounting it on navigation.
  const [zoomed, setZoomed] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") onPrev();
      else if (e.key === "ArrowRight") onNext();
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose, onPrev, onNext]);

  const video = isVideo(entry.name);

  return (
    <div className="overlay viewer" role="dialog" aria-modal="true">
      <button
        type="button"
        className="viewer-close"
        aria-label="Close"
        onClick={onClose}
      >
        ✕
      </button>
      <button
        type="button"
        className="viewer-nav prev"
        aria-label="Previous"
        onClick={onPrev}
      >
        ‹
      </button>
      <div className="viewer-stage" onClick={onClose}>
        {video ? (
          <video
            className="viewer-video"
            src={url}
            controls
            autoPlay
            onClick={(e) => {
              e.stopPropagation();
            }}
          />
        ) : isImage(entry.name) ? (
          <img
            className={zoomed ? "viewer-img zoomed" : "viewer-img"}
            src={url}
            alt={entry.name}
            onClick={(e) => {
              e.stopPropagation();
              setZoomed((z) => !z);
            }}
          />
        ) : (
          <div className="viewer-fallback">
            <p>{entry.name}</p>
            <a href={url} download>
              Download
            </a>
          </div>
        )}
      </div>
      <button
        type="button"
        className="viewer-nav next"
        aria-label="Next"
        onClick={onNext}
      >
        ›
      </button>
      <div className="viewer-caption">{entry.name}</div>
    </div>
  );
}
