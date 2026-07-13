import type { ProtocolExtractRuleItem } from '#/api/protocol-compliance';

export type WorkbenchStage =
  | 'assert_gen'
  | 'code_locate'
  | 'done'
  | 'fuzz'
  | 'rule_confirm'
  | 'setup';

export type StageStatus = 'done' | 'error' | 'idle' | 'running' | 'skipped';

export interface CodeLocateRow {
  emphasis?: boolean;
  line: number | string;
  text: string;
}

export interface CodeLocateFunctionSlice {
  codeRows: CodeLocateRow[];
  name: string;
  path?: string;
  targetLine?: number | string;
}

export interface CodeLocateEvidence {
  candidateFunctionCount: number;
  codeRows: CodeLocateRow[];
  functions?: CodeLocateFunctionSlice[];
  keySliceCount: number;
  relatedVariableCount: number;
  resultLabel?: string;
  ruleText?: string;
  source?: string;
  targetFile: string;
  targetLine: string;
  updatedAt?: string;
  violationReason?: string;
}

export interface ProjectConfig {
  archive: File | null;
  rules: File | null;
  notes: string;
}

export interface RuleOption extends ProtocolExtractRuleItem {
  id?: string;
  msgType?: string;
}

export const STAGE_LIST: Array<{
  index: number;
  key: WorkbenchStage;
  title: string;
}> = [
  { key: 'rule_confirm', index: 1, title: '规则确认' },
  { key: 'code_locate', index: 2, title: '代码定位与一致性分析' },
  { key: 'assert_gen', index: 3, title: '断言生成' },
  { key: 'fuzz', index: 4, title: '模糊测试' },
  { key: 'done', index: 5, title: 'AFL 结果' },
];
