import { faker } from '@faker-js/faker';
import { eventHandler, readMultipartFormData, setResponseStatus } from 'h3';
import { verifyAccessToken } from '~/utils/jwt-utils';
import {
  unAuthorizedResponse,
  useResponseError,
  useResponseSuccess,
} from '~/utils/response';

interface BuildAnalysisOptions {
  codeFileName: string;
  notes?: string;
  protocolName: string;
  rulesFileName: string;
  rulesSummary?: string;
}

type ComplianceStatus = 'compliant' | 'needs_review' | 'non_compliant';

interface LlmEntry {
  category: string;
  compliance: ComplianceStatus;
  confidence: 'high' | 'low' | 'medium';
  explanation: string;
  findingId: string;
  lineRange?: [number, number];
  location: {
    file: string;
    function?: string;
  };
  recommendation?: string;
  relatedRule: {
    id: string;
    requirement: string;
    source: string;
  };
}

function buildMockAnalysis(options: BuildAnalysisOptions) {
  const now = new Date().toISOString();
  const entryCount = faker.number.int({ max: 6, min: 4 });
  const findings: LlmEntry[] = Array.from({ length: entryCount }, () => {
    const compliance = faker.helpers.arrayElement<ComplianceStatus>([
      'compliant',
      'non_compliant',
      'needs_review',
    ]);
    const findingId = faker.string.uuid();
    const requirement = faker.lorem.sentence({ max: 18, min: 10 });
    const source = `RFC ${faker.number.int({ max: 8999, min: 1000 })} Section ${faker.number.int({ max: 6, min: 1 })}.${faker.number.int({ max: 9, min: 1 })}`;
    const baseExplanation = faker.lorem.paragraph();
    const recommendation =
      compliance === 'non_compliant'
        ? faker.lorem.sentence({ max: 18, min: 12 })
        : undefined;
    const lineStart = faker.number.int({ max: 320, min: 12 });
    const lineEnd = lineStart + faker.number.int({ max: 14, min: 2 });

    return {
      category: faker.helpers.arrayElement([
        '状态机约束',
        '消息字段校验',
        '握手流程',
        '错误处理',
      ]),
      compliance,
      confidence: faker.helpers.arrayElement(['low', 'medium', 'high']),
      explanation: baseExplanation,
      findingId,
      lineRange: [lineStart, lineEnd],
      location: {
        file: options.codeFileName,
        function: faker.helpers.arrayElement([
          'handle_handshake',
          'process_record',
          'validate_request',
          'dispatch_message',
        ]),
      },
      recommendation,
      relatedRule: {
        id: `RULE-${faker.number.int({ max: 999, min: 101 })}`,
        requirement,
        source,
      },
    };
  });

  const statusCounts: Record<ComplianceStatus, number> = {
    compliant: 0,
    needs_review: 0,
    non_compliant: 0,
  };

  for (const finding of findings) {
    statusCounts[finding.compliance] += 1;
  }

  let overallStatus: ComplianceStatus;
  if (statusCounts.non_compliant > 0) {
    overallStatus = 'non_compliant';
  } else if (statusCounts.needs_review > 0) {
    overallStatus = 'needs_review';
  } else {
    overallStatus = 'compliant';
  }

  return {
    analysisId: faker.string.uuid(),
    durationMs: faker.number.int({ max: 4200, min: 1800 }),
    inputs: {
      codeFileName: options.codeFileName,
      notes: options.notes ?? null,
      protocolName: options.protocolName,
      rulesFileName: options.rulesFileName,
      rulesSummary: options.rulesSummary ?? null,
    },
    model: 'protocol-guard-static-preview',
    modelResponse: {
      metadata: {
        generatedAt: now,
        modelVersion: 'protocol-guard-llm-2024-10',
        protocol: options.protocolName,
        ruleSet: options.rulesFileName,
      },
      summary: {
        compliantCount: statusCounts.compliant,
        needsReviewCount: statusCounts.needs_review,
        nonCompliantCount: statusCounts.non_compliant,
        notes:
          options.notes ??
          '本次静态检测通过 ProtocolGuard 原型进行（Mock 数据）。',
        overallStatus,
      },
      verdicts: findings,
    },
    submittedAt: now,
  };
}

function normalizeProtocolName(parsedRules: any, fallback: string) {
  if (!parsedRules || typeof parsedRules !== 'object') {
    return fallback;
  }
  if (typeof parsedRules.protocol === 'string') {
    return parsedRules.protocol;
  }
  if (typeof parsedRules.protocolName === 'string') {
    return parsedRules.protocolName;
  }
  if (typeof parsedRules.title === 'string') {
    return parsedRules.title;
  }
  if (typeof parsedRules.name === 'string') {
    return parsedRules.name;
  }
  return fallback;
}

function tryExtractRulesSummary(parsedRules: any): string | undefined {
  if (!parsedRules || typeof parsedRules !== 'object') {
    return undefined;
  }
  if (typeof parsedRules.summary === 'string') {
    return parsedRules.summary;
  }
  if (typeof parsedRules.description === 'string') {
    return parsedRules.description;
  }
  if (Array.isArray(parsedRules.rules) && parsedRules.rules.length > 0) {
    const first = parsedRules.rules[0];
    if (first && typeof first === 'object' && 'requirement' in first) {
      return `包含 ${parsedRules.rules.length} 条规则，示例：${first.requirement}`;
    }
  }
  return undefined;
}

export default eventHandler(async (event) => {
  const user = verifyAccessToken(event);
  if (!user) {
    return unAuthorizedResponse(event);
  }

  const formData = await readMultipartFormData(event);
  if (!formData?.length) {
    setResponseStatus(event, 400);
    return useResponseError('请上传协议规则和代码片段');
  }

  let rulesFileName: string | undefined;
  let codeFileName: string | undefined;
  let notes: string | undefined;
  let parsedRules: any;

  for (const item of formData) {
    if (!item.name) {
      continue;
    }
    if (item.filename) {
      if (item.name === 'rules') {
        rulesFileName = item.filename;
        const buffer = item.data;
        if (buffer) {
          try {
            const text = buffer.toString('utf8');
            parsedRules = JSON.parse(text);
          } catch {
            // ignore parse errors; fall back to defaults
          }
        }
      } else if (item.name === 'code') {
        codeFileName = item.filename;
      }
      continue;
    }
    if (item.name === 'notes') {
      notes = item.data?.toString('utf8');
    }
  }

  if (!rulesFileName || !codeFileName) {
    setResponseStatus(event, 400);
    return useResponseError('请同时上传协议规则 JSON 和代码片段文件');
  }

  const protocolName = normalizeProtocolName(parsedRules, rulesFileName);
  const rulesSummary = tryExtractRulesSummary(parsedRules);

  const analysis = buildMockAnalysis({
    codeFileName,
    notes,
    protocolName,
    rulesFileName,
    rulesSummary,
  });

  return useResponseSuccess(analysis);
});
