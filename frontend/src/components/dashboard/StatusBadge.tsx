import { Badge } from '../../components/ui/badge';
import { getStatusColor } from '../../lib/api-utils';

interface StatusBadgeProps {
  status: string;
  failureReason?: string;
}

export function StatusBadge({ status, failureReason }: StatusBadgeProps) {
  const colors = getStatusColor(status);
  const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <div className="flex flex-col gap-1">
      <Badge
        variant="outline"
        className={`${colors.bg} ${colors.text} ${colors.border} border font-medium`}
      >
        {statusLabel}
      </Badge>
      {failureReason && (
        <p className="text-xs text-red-600 font-medium">{failureReason}</p>
      )}
    </div>
  );
}
