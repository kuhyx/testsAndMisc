import { useMemo, useRef, useState } from "react";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";
import { crumbs, isImage, isVideo } from "../lib/paths.ts";
import { useHashPath } from "../lib/use-hash-path.ts";
import { useListing } from "../hooks/use-listing.ts";
import { Grid } from "./grid.tsx";
import { MediaViewer } from "./media-viewer.tsx";
import { TextEditor } from "./text-editor.tsx";
import { ConfirmDialog } from "./confirm-dialog.tsx";

export function Gallery({ client }: { readonly client: DufsClient }): React.JSX.Element {
  const [path, navigate] = useHashPath();
  const { entries, loading, error, reload } = useListing(client, path);
  // -1 means "no viewer open" (avoids a null branch in step()).
  const [viewerIndex, setViewerIndex] = useState(-1);
  const [editEntry, setEditEntry] = useState<DirEntry | null>(null);
  const [deleteEntry, setDeleteEntry] = useState<DirEntry | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const media = useMemo(
    () => entries.filter((e) => isImage(e.name) || isVideo(e.name)),
    [entries],
  );

  // Grid only calls this for media entries, so the entry is always in `media`.
  function openMedia(entry: DirEntry): void {
    setViewerIndex(media.findIndex((m) => m.path === entry.path));
  }

  function step(delta: number): void {
    setViewerIndex((cur) => (cur + delta + media.length) % media.length);
  }

  function onUploadPicked(files: FileList | null): void {
    if (files === null || files.length === 0) return;
    setBusy(`Uploading ${files.length} file(s)…`);
    void (async () => {
      try {
        for (const file of Array.from(files)) {
          await client.upload(path, file);
        }
        reload();
      } catch (err: unknown) {
        setBusy(err instanceof Error ? err.message : String(err));
        return;
      }
      setBusy(null);
    })();
  }

  function confirmDelete(entry: DirEntry): void {
    setDeleteEntry(null);
    setBusy(`Deleting ${entry.name}…`);
    client
      .remove(entry.path)
      .then(() => {
        setBusy(null);
        reload();
      })
      .catch((err: unknown) => {
        setBusy(err instanceof Error ? err.message : String(err));
      });
  }

  const viewerEntry = viewerIndex >= 0 ? media[viewerIndex] : null;

  return (
    <div className="gallery">
      <header className="topbar">
        <nav className="crumbs" aria-label="Breadcrumb">
          {crumbs(path).map((c, i, all) => (
            <span key={c.path}>
              <button
                type="button"
                className="crumb"
                onClick={() => {
                  navigate(c.path);
                }}
              >
                {c.name}
              </button>
              {i < all.length - 1 && <span className="crumb-sep">/</span>}
            </span>
          ))}
        </nav>
        <div className="tools">
          {busy !== null && <span className="busy">{busy}</span>}
          <button
            type="button"
            className="primary"
            onClick={() => {
              fileInput.current?.click();
            }}
          >
            Upload
          </button>
          <input
            ref={fileInput}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              onUploadPicked(e.target.files);
              e.target.value = "";
            }}
          />
        </div>
      </header>

      <main className="content">
        {loading && <p className="muted">Loading…</p>}
        {error !== null && <p className="error">Could not load: {error}</p>}
        {!loading && error === null && entries.length === 0 && (
          <p className="muted">This folder is empty.</p>
        )}
        {!loading && error === null && entries.length > 0 && (
          <Grid
            client={client}
            entries={entries}
            onOpenDir={navigate}
            onOpenMedia={openMedia}
            onEditText={setEditEntry}
            onDelete={setDeleteEntry}
          />
        )}
      </main>

      {viewerEntry && (
        <MediaViewer
          key={viewerEntry.path}
          entry={viewerEntry}
          url={client.fileUrl(viewerEntry.path)}
          onClose={() => {
            setViewerIndex(-1);
          }}
          onPrev={() => {
            step(-1);
          }}
          onNext={() => {
            step(1);
          }}
        />
      )}
      {editEntry && (
        <TextEditor
          client={client}
          entry={editEntry}
          onClose={() => {
            setEditEntry(null);
            reload();
          }}
        />
      )}
      {deleteEntry && (
        <ConfirmDialog
          message={`Delete "${deleteEntry.name}"? This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={() => {
            confirmDelete(deleteEntry);
          }}
          onCancel={() => {
            setDeleteEntry(null);
          }}
        />
      )}
    </div>
  );
}
