import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * cn — the single className combiner for the app.
 *
 * clsx handles conditional/record syntax; twMerge resolves conflicting
 * Tailwind utilities (later wins). Replace the legacy hand-rolled joiner
 * in src/ui/cn.ts (which only concatenated strings) with this everywhere
 * during the staged refactor.
 *
 * Import from "@/lib/cn".
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
