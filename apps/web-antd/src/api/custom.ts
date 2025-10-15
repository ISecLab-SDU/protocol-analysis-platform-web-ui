import { requestClient } from './request';

export interface FuzzTextResponse {
  text: string;
}

export function getFuzzText() {
  return requestClient.get<FuzzTextResponse>('/custom/text');
}


