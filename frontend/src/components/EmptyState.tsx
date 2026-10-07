interface EmptyStateProps {
  message?: string;
}

export default function EmptyState({ message = "Nothing to show yet." }: EmptyStateProps) {
  return <div className="flex items-center justify-center p-8 text-gray-400">{message}</div>;
}
