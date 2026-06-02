import { useRef, useEffect, useState } from "react";

interface Props {
  facingMode?: "environment" | "user";
  onCapture: (blob: Blob) => void;
  onClose: () => void;
}

export function CameraCapture({
  facingMode = "environment",
  onCapture,
  onClose,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode, width: { ideal: 1280 }, height: { ideal: 960 } } })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => setReady(true);
        }
      })
      .catch(() => setError("Camera access denied"));

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [facingMode]);

  const handleCapture = () => {
    const video = videoRef.current;
    if (!video) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          streamRef.current?.getTracks().forEach((t) => t.stop());
          onCapture(blob);
        }
      },
      "image/jpeg",
      0.85,
    );
  };

  if (error) {
    return (
      <div className="camera-overlay">
        <div className="camera__error">
          <p>{error}</p>
          <button className="btn btn--primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="camera-overlay">
      <button className="camera__close" onClick={onClose}>
        &times;
      </button>
      <video
        ref={videoRef}
        className="camera__viewfinder"
        autoPlay
        playsInline
        muted
      />
      {ready && (
        <button className="camera__capture-btn" onClick={handleCapture}>
          <span className="camera__capture-ring" />
        </button>
      )}
    </div>
  );
}
