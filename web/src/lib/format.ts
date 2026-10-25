export const formatBytes = (size: number) => {
  if (size < 1024) {
    return `${size} B`;
  }
  const units = ["KB", "MB", "GB"];
  let unitIndex = -1;
  let value = size;
  do {
    value /= 1024;
    unitIndex += 1;
  } while (value >= 1024 && unitIndex < units.length - 1);
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
};

export const formatDuration = (seconds: number) => {
  if (seconds < 10) {
    return `${seconds.toFixed(1)} s`;
  }
  if (seconds < 90) {
    return `${Math.round(seconds)} s`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes} min ${rest.toString().padStart(2, "0")} s`;
};

/** Coarse "about N left" text that doesn't flicker on every update. */
export const formatEta = (seconds: number) => {
  if (seconds < 5) {
    return "a few seconds left";
  }
  if (seconds < 60) {
    return `about ${Math.ceil(seconds / 5) * 5} s left`;
  }
  return `about ${Math.ceil(seconds / 60)} min left`;
};

export const encodeTextToBase64 = (text: string) => {
  const bytes = new TextEncoder().encode(text);
  const chunkSize = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(
      ...bytes.subarray(offset, offset + chunkSize),
    );
  }
  return btoa(binary);
};

export const readFileAsBase64 = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      const base64 =
        typeof result === "string" ? result.split(",", 2)[1] : null;
      if (base64) {
        resolve(base64);
      } else {
        reject(new Error("Could not read the file."));
      }
    };
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsDataURL(file);
  });
