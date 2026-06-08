type EmptyStateProps = {
  icon?: React.ReactNode;
  message: string;
};

export function EmptyState({ icon, message }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      {icon && <div className="text-slate-600">{icon}</div>}
      <p className="text-sm text-slate-500 max-w-xs">{message}</p>
    </div>
  );
}
