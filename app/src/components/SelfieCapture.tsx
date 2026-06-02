import { useState } from "react";
import { CameraCapture } from "./CameraCapture";

interface Props {
  onCapture: (blob: Blob) => void;
  onSkip: () => void;
}

export function SelfieCapture({ onCapture, onSkip }: Props) {
  const [preview, setPreview] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);

  if (!preview) {
    return (
      <div className="selfie-capture">
        <CameraCapture
          facingMode="user"
          onCapture={(b) => {
            setBlob(b);
            setPreview(URL.createObjectURL(b));
          }}
          onClose={onSkip}
        />
      </div>
    );
  }

  return (
    <div className="selfie-preview-overlay">
      <img className="selfie-preview__img" src={preview} alt="Selfie preview" />
      <div className="selfie-preview__actions">
        <button
          className="btn btn--primary btn--full"
          onClick={() => blob && onCapture(blob)}
        >
          Use Photo
        </button>
        <button
          className="btn btn--full"
          onClick={() => {
            URL.revokeObjectURL(preview);
            setPreview(null);
            setBlob(null);
          }}
        >
          Retake
        </button>
        <button className="btn btn--full modal__skip" onClick={onSkip}>
          Skip selfie
        </button>
      </div>
    </div>
  );
}
