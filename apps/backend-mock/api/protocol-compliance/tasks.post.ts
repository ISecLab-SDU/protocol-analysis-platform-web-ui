import {
  eventHandler,
  getRequestURL,
  readMultipartFormData,
  setResponseStatus,
} from 'h3';
import { verifyAccessToken } from '~/utils/jwt-utils';
import {
  createProtocolComplianceTask,
  serializeProtocolComplianceTask,
} from '~/utils/protocol-compliance-store';
import {
  unAuthorizedResponse,
  useResponseError,
  useResponseSuccess,
} from '~/utils/response';

export default eventHandler(async (event) => {
  const user = verifyAccessToken(event);
  if (!user) {
    return unAuthorizedResponse(event);
  }

  const formData = await readMultipartFormData(event);
  if (!formData?.length) {
    setResponseStatus(event, 400);
    return useResponseError('请上传协议文档');
  }

  const fields: Record<string, string> = {};
  let documentName: string | undefined;
  let documentSize: number | undefined;

  for (const item of formData) {
    if (!item.name) {
      continue;
    }
    if (item.filename) {
      documentName = item.filename;
      documentSize = item.data?.length;
      continue;
    }
    fields[item.name] = item.data?.toString('utf8') ?? '';
  }

  if (!documentName) {
    setResponseStatus(event, 400);
    return useResponseError('缺少协议文档，请重新上传');
  }

  const description = fields.description?.trim() || undefined;
  const name =
    fields.name?.trim() || documentName.replace(/\.[^/.]+$/, '') || '协议任务';

  let tags: string[] | undefined;
  if (fields.tags) {
    try {
      const parsed = JSON.parse(fields.tags);
      if (Array.isArray(parsed)) {
        tags = parsed.filter(
          (item): item is string => typeof item === 'string',
        );
      }
    } catch {
      // ignore parse error, treat as no tags provided
    }
  }

  const task = createProtocolComplianceTask({
    description,
    documentName,
    documentSize,
    name,
    tags,
  });

  const requestUrl = getRequestURL(event);

  return useResponseSuccess(serializeProtocolComplianceTask(task, requestUrl));
});
