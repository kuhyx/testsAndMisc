interface ConfirmDialogProps {
  readonly message: string;
  readonly confirmLabel: string;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

/** A small modal confirm used to guard destructive actions (delete). */
export function ConfirmDialog({
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: ConfirmDialogProps): React.JSX.Element {
  return (
    <div className="overlay" role="dialog" aria-modal="true" onClick={onCancel}>
      <div
        className="dialog"
        onClick={(e) => {
          e.stopPropagation();
        }}
      >
        <p>{message}</p>
        <div className="dialog-actions">
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="danger" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
