import { eventHandler, getRouterParam, setHeader, setResponseStatus } from 'h3';
import { verifyAccessToken } from '~/utils/jwt-utils';
import { getProtocolComplianceTask } from '~/utils/protocol-compliance-store';
import { unAuthorizedResponse, useResponseError } from '~/utils/response';

function buildFileName(name: string) {
  return `${name.replaceAll(/\s+/g, '-')}-rules.json`;
}

export default eventHandler(async (event) => {
  const user = verifyAccessToken(event);
  if (!user) {
    return unAuthorizedResponse(event);
  }

  const taskId = getRouterParam(event, 'id');
  if (!taskId) {
    setResponseStatus(event, 400);
    return useResponseError('缺少任务编号');
  }

  const task = getProtocolComplianceTask(taskId);
  if (!task) {
    setResponseStatus(event, 404);
    return useResponseError('未找到指定任务');
  }

  if (task.status !== 'completed' || !task.resultPayload) {
    setResponseStatus(event, 409);
    return useResponseError('任务尚未完成，暂不可下载结果');
  }

  const fileName = buildFileName(task.name || task.documentName);
  const content = JSON.stringify(task.resultPayload, null, 2);

  setHeader(event, 'Content-Type', 'application/json; charset=utf-8');
  setHeader(
    event,
    'Content-Disposition',
    `attachment; filename="${encodeURIComponent(fileName)}"`,
  );

  return content;
});
