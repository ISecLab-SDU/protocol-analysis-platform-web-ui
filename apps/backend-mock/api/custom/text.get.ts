import { defineEventHandler } from 'h3';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { useResponseSuccess } from '../../utils/response';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineEventHandler(async () => {
  const localPath = resolve(__dirname, './fuzz_output.txt');
  let text: string | null = null;
  try {
    text = await readFile(localPath, 'utf-8');
  } catch {}

  if (!text || text.trim().length === 0) {
    const rootPath = resolve(__dirname, '../../../../fuzz_output.txt');
    try {
      text = await readFile(rootPath, 'utf-8');
    } catch {}
  }

  return useResponseSuccess({ text: text ?? '' });
});


