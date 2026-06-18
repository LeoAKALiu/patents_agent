/**
 * Returns a filesystem-safe project name suitable for download attributes.
 *
 * Mirrors the backend's Content-Disposition sanitization in
 * backend/app/main.py::_content_disposition_header, which replaces
 * path separators with underscores and strips whitespace.
 *
 * @param name - The raw project name (may be undefined/null).
 * @param fallback - Fallback name when the raw name is empty/missing.
 * @returns A filename-safe string with no path separators or control characters.
 */
export function safeProjectName(name: string | undefined | null, fallback = "专利草稿"): string {
  const raw = (name || fallback).trim();
  // Replace characters that are unsafe or disruptive in filesystem paths.
  // Backend equivalent: filename.replace("/", "_").replace("\\", "_").strip()
  // We also catch additional characters that cause issues across OSes.
  const safe = raw.replace(/[\/\\:*?"<>|]/g, "_").trim();
  return safe || fallback;
}
