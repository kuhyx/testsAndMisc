import React, { useState } from "react";
import type { FileGameResult, TransferMode } from "../types";
import { fileIcon, formatSize } from "../lib/fileIcon";
import { zipDownload } from "../lib/zipDownload";
import { uploadFiles } from "../lib/uploadFiles";
import styles from "./ScoreScreen.module.css";

interface Props {
  result: FileGameResult;
  mode: TransferMode;
  onRestart: () => void;
}

type ActionState = "idle" | "working" | "done" | "error";

function calcGrade(pct: number): string {
  if (pct >= 90) return "S";
  if (pct >= 75) return "A";
  if (pct >= 50) return "B";
  if (pct >= 25) return "C";
  return "D";
}

export function ScoreScreen({
  result,
  mode,
  onRestart,
}: Props): React.ReactElement {
  const [state, setState] = useState<ActionState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const total = result.caught.length + result.missed.length;
  const pct =
    total === 0 ? 0 : Math.round((result.caught.length / total) * 100);
  const grade = calcGrade(pct);

  const handleAction = async (): Promise<void> => {
    setState("working");
    try {
      if (mode === "download") {
        await zipDownload(result.caught);
      } else {
        await uploadFiles(result.caught);
      }
      setState("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setState("error");
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.scoreBox}>
        <div className={styles.grade}>{grade}</div>
        <div className={styles.pct}>{pct}%</div>
        <div className={styles.stats}>
          <span className={styles.caught}>✅ {result.caught.length} caught</span>
          <span className={styles.missed}>❌ {result.missed.length} missed</span>
        </div>
      </div>

      <div className={styles.lists}>
        {result.caught.length > 0 && (
          <div>
            <h3 className={styles.listTitle}>Caught</h3>
            <ul className={styles.fileList}>
              {result.caught.map((f, i) => (
                <li key={i} className={styles.fileItem}>
                  <span>{fileIcon(f)}</span>
                  <span className={styles.fname}>{f.name}</span>
                  <span className={styles.fsize}>{formatSize(f.size)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {result.missed.length > 0 && (
          <div>
            <h3 className={styles.listTitle}>Missed</h3>
            <ul className={styles.fileList}>
              {result.missed.map((f, i) => (
                <li key={i} className={`${styles.fileItem} ${styles.missedItem}`}>
                  <span>{fileIcon(f)}</span>
                  <span className={styles.fname}>{f.name}</span>
                  <span className={styles.fsize}>{formatSize(f.size)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className={styles.actions}>
        {result.caught.length > 0 && state === "idle" && (
          <button className={styles.actionBtn} onClick={() => void handleAction()}>
            {mode === "download"
              ? `⬇️ Download ${result.caught.length} caught file${result.caught.length !== 1 ? "s" : ""}`
              : `☁️ Upload ${result.caught.length} caught file${result.caught.length !== 1 ? "s" : ""} to server`}
          </button>
        )}
        {state === "working" && (
          <p className={styles.status}>Working…</p>
        )}
        {state === "done" && (
          <p className={styles.status}>
            {mode === "download" ? "Downloaded!" : "Uploaded to server!"}
          </p>
        )}
        {state === "error" && (
          <p className={styles.error}>Error: {errorMsg}</p>
        )}
        <button className={styles.restartBtn} onClick={onRestart}>
          Play again
        </button>
      </div>
    </div>
  );
}
