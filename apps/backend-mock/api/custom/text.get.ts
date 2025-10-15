import { defineEventHandler } from 'h3';
import { readFile } from 'node:fs/promises';
import { access } from 'node:fs/promises';
import { constants } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { useResponseSuccess } from '../../utils/response';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineEventHandler(async () => {
  // Try multiple candidate locations to make dev-server resilient
  const candidates = [
    // 1) Next to this file (works if Nitro bundles the asset here)
    resolve(__dirname, './fuzz_output.txt'),
    // 2) When CWD is the mock package (Nitro dev rootDir)
    resolve(process.cwd(), 'api/custom/fuzz_output.txt'),
    // 3) When CWD is monorepo root
    resolve(process.cwd(), 'apps/backend-mock/api/custom/fuzz_output.txt'),
  ];

  let text: string | null = null;
  for (const p of candidates) {
    try {
      await access(p, constants.R_OK);
      const content = await readFile(p, 'utf-8');
      if (content && content.trim().length > 0) {
        text = content;
        break;
      }
    } catch {
      // try next path
    }
  }

  return useResponseSuccess({ text: text ?? '' });
});


