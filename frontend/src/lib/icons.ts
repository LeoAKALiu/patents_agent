/**
 * Central lucide icon registry.
 *
 * One import surface for the whole app: `import { FileText, RefreshCw } from "@/lib/icons"`.
 * Re-exporting from here (instead of scattering `from "lucide-react"` across files)
 * gives us a single place to audit/swap the icon set, and stops ad-hoc inline SVGs
 * (e.g. the refresh <svg> in ShellTopbar.tsx) from drifting.
 *
 * Add new icons here as views migrate. Type-only (`type LucideIcon`) re-exports
 * stay separate so tree-shaking keeps them out of the icon runtime bundle.
 */
export {
  AlertTriangle,
  BarChart3,
  BookOpen,
  CheckCircle2,
  CircleSlash,
  ClipboardCheck,
  ClipboardList,
  Clock,
  Database,
  Download,
  Eye,
  EyeOff,
  FileArchive,
  FilePlus2,
  FileText,
  FolderKanban,
  Gauge,
  HelpCircle,
  Info,
  KeyRound,
  Loader2,
  LockKeyhole,
  Monitor,
  Moon,
  PenLine,
  PlayCircle,
  RefreshCw,
  Save,
  Scale,
  Search,
  SearchCheck,
  Settings,
  ShieldCheck,
  Sigma,
  Sun,
  Trash2,
  Upload,
  UsersRound,
  Wand2,
  XCircle,
} from "lucide-react";

export type { LucideIcon } from "lucide-react";
