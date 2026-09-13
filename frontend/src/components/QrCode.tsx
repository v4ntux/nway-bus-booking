import { useEffect, useState } from "react";
import QRCode from "qrcode";

/**
 * Renders the boarding token as a scannable code. Drawn light-on-dark
 * independent of theme: scanners need real contrast, not a themed one.
 */
export function QrCode({ value, size = 176 }: { value: string; size?: number }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    QRCode.toDataURL(value, {
      width: size * 2,
      margin: 1,
      errorCorrectionLevel: "M",
      color: { dark: "#15181b", light: "#ffffff" },
    })
      .then((url) => alive && setSrc(url))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [value, size]);

  if (failed) {
    return (
      <p className="tnum break-all rounded-control bg-white p-3 text-center text-[11px] text-[#15181b]">
        {value}
      </p>
    );
  }

  return (
    <div
      className="flex items-center justify-center rounded-control bg-white p-2"
      style={{ width: size + 16, height: size + 16 }}
    >
      {src ? (
        <img src={src} alt="Chipta QR-kodi" width={size} height={size} />
      ) : (
        <span className="skeleton block h-full w-full" />
      )}
    </div>
  );
}
