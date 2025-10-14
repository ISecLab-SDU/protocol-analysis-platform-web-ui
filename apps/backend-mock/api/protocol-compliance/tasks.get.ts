import { eventHandler, getQuery, getRequestURL, setResponseStatus } from 'h3';
import { verifyAccessToken } from '~/utils/jwt-utils';
import {
  listProtocolComplianceTasks,
  ProtocolComplianceTaskStatus,
  serializeProtocolComplianceTask,
} from '~/utils/protocol-compliance-store';
import {
  unAuthorizedResponse,
  useResponseError,
  useResponseSuccess,
} from '~/utils/response';

function toNumber(value: unknown, fallback: number) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function normalizeStatus(
  input: unknown,
): ProtocolComplianceTaskStatus[] | undefined {
  const rawValues = Array.isArray(input) ? input : [input];
  const allowedStatuses = new Set<ProtocolComplianceTaskStatus>([
    'completed',
    'failed',
    'processing',
    'queued',
  ]);
  const collected = new Set<ProtocolComplianceTaskStatus>();

  for (const value of rawValues) {
    if (typeof value !== 'string') {
      continue;
    }
    const segments = value.split(',').map((item) => item.trim());
    for (const segment of segments) {
      if (allowedStatuses.has(segment as ProtocolComplianceTaskStatus)) {
        collected.add(segment as ProtocolComplianceTaskStatus);
      }
    }
  }

  return collected.size > 0 ? [...collected] : undefined;
}

export default eventHandler((event) => {
  const user = verifyAccessToken(event);
  if (!user) {
    return unAuthorizedResponse(event);
  }

  const query = getQuery(event);
  const page = toNumber(query.page, 1);
  const pageSize = Math.min(toNumber(query.pageSize, 20), 50);
  const statusFilter = normalizeStatus(query.status);

  const allTasks = listProtocolComplianceTasks({
    status: statusFilter,
  });
  const total = allTasks.length;
  const start = (page - 1) * pageSize;
  const items = allTasks.slice(start, start + pageSize);

  const requestUrl = getRequestURL(event);
  const responseItems = items.map((task) =>
    serializeProtocolComplianceTask(task, requestUrl),
  );

  if (page > 1 && responseItems.length === 0 && total > 0) {
    setResponseStatus(event, 400);
    return useResponseError('Requested page exceeds available data');
  }

  return useResponseSuccess({
    items: responseItems,
    page,
    pageSize,
    total,
  });
});
