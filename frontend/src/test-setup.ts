import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
}

function ensureLocalStorage() {
  if (typeof window === "undefined") return;
  try {
    if (window.localStorage) return;
  } catch {
    // Replace inaccessible storage below.
  }
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: createMemoryStorage(),
  });
}

ensureLocalStorage();
beforeEach(ensureLocalStorage);
