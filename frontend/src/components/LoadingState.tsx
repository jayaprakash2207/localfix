interface LoadingStateProps {
  label?: string;
}

export default function LoadingState({ label = "Loading..." }: LoadingStateProps) {
  return (
    <div role="status" className="flex items-center justify-center p-8 text-gray-500">
      {label}
    </div>
  );
}
