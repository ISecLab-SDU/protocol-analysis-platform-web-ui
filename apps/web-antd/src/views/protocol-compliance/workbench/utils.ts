/**
 * ANSI escape sequence to HTML converter, supports SGR codes (colors, bold,
 * italic, underline, etc.) and ignores cursor/erase sequences.
 */

const ESC = String.fromCharCode(0x1B);

const ANSI_STANDARD_COLORS = [
  '#000000',
  '#AA0000',
  '#00AA00',
  '#AA5500',
  '#0000AA',
  '#AA00AA',
  '#00AAAA',
  '#AAAAAA',
] as const;

const ANSI_BRIGHT_COLORS = [
  '#555555',
  '#FF5555',
  '#55FF55',
  '#FFFF55',
  '#5555FF',
  '#FF55FF',
  '#55FFFF',
  '#FFFFFF',
] as const;

const ANSI_ESCAPE_PATTERN = new RegExp(
  `${ESC}\\[(\\d{1,3}(?:;\\d{1,3})*)m`,
  'g',
);
const ANSI_CSI_NON_SGR = new RegExp(`${ESC}\\[[0-9;?]*[A-HJKSTfnisu]`, 'g');
const ANSI_OSC = new RegExp(`${ESC}\\][^\\u0007]*(?:\\u0007|${ESC}\\\\)`, 'g');

interface AnsiStyleState {
  color: null | string;
  backgroundColor: null | string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
  strikethrough: boolean;
  dim: boolean;
  conceal: boolean;
}

const defaultAnsiStyleState: AnsiStyleState = {
  backgroundColor: null,
  bold: false,
  color: null,
  conceal: false,
  dim: false,
  italic: false,
  strikethrough: false,
  underline: false,
};

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function clamp(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(255, Math.round(value)));
}

function toHexComponent(value: number) {
  return clamp(value).toString(16).padStart(2, '0');
}

function rgbToHex(r: number, g: number, b: number) {
  return `#${toHexComponent(r)}${toHexComponent(g)}${toHexComponent(b)}`;
}

function ansi256ToHex(index: number): null | string {
  if (index >= 0 && index <= 7) return ANSI_STANDARD_COLORS[index] ?? null;
  if (index >= 8 && index <= 15) return ANSI_BRIGHT_COLORS[index - 8] ?? null;
  if (index >= 16 && index <= 231) {
    const base = index - 16;
    const r = Math.floor(base / 36);
    const g = Math.floor((base % 36) / 6);
    const b = base % 6;
    const resolve = (c: number) => (c === 0 ? 0 : c * 40 + 55);
    return rgbToHex(resolve(r), resolve(g), resolve(b));
  }
  if (index >= 232 && index <= 255) {
    const gray = 8 + (index - 232) * 10;
    return rgbToHex(gray, gray, gray);
  }
  return null;
}

function buildStyleString(state: AnsiStyleState) {
  const decls: string[] = [];
  if (state.conceal) decls.push('color: transparent', 'text-shadow: none');
  else if (state.color) decls.push(`color: ${state.color}`);
  if (state.backgroundColor)
    decls.push(`background-color: ${state.backgroundColor}`);
  if (state.bold) decls.push('font-weight: 600');
  if (state.italic) decls.push('font-style: italic');
  const td: string[] = [];
  if (state.underline) td.push('underline');
  if (state.strikethrough) td.push('line-through');
  if (td.length > 0) decls.push(`text-decoration: ${td.join(' ')}`);
  if (state.dim) decls.push('opacity: 0.75');
  return decls.join('; ');
}

function hasStyle(state: AnsiStyleState) {
  return Boolean(
    state.conceal ||
      state.color ||
      state.backgroundColor ||
      state.bold ||
      state.italic ||
      state.underline ||
      state.strikethrough ||
      state.dim,
  );
}

function reset(target: AnsiStyleState) {
  Object.assign(target, defaultAnsiStyleState);
}

function applyCodes(state: AnsiStyleState, codes: number[]) {
  if (codes.length === 0) {
    reset(state);
    return;
  }
  for (let i = 0; i < codes.length; i += 1) {
    const codeRaw = codes[i];
    if (!Number.isFinite(codeRaw)) continue;
    const code = Number(codeRaw);
    switch (code) {
      case 0: {
        reset(state);
        break;
      }
      case 1: {
        state.bold = true;
        state.dim = false;
        break;
      }
      case 2: {
        state.dim = true;
        state.bold = false;
        break;
      }
      case 3: {
        state.italic = true;
        break;
      }
      case 4:
      case 21: {
        state.underline = true;
        break;
      }
      case 8: {
        state.conceal = true;
        break;
      }
      case 9: {
        state.strikethrough = true;
        break;
      }
      case 22: {
        state.bold = false;
        state.dim = false;
        break;
      }
      case 23: {
        state.italic = false;
        break;
      }
      case 24: {
        state.underline = false;
        break;
      }
      case 28: {
        state.conceal = false;
        break;
      }
      case 29: {
        state.strikethrough = false;
        break;
      }
      case 39: {
        state.color = null;
        state.conceal = false;
        break;
      }
      case 49: {
        state.backgroundColor = null;
        break;
      }
      default: {
        if (code >= 30 && code <= 37) {
          state.color = ANSI_STANDARD_COLORS[code - 30] ?? null;
          state.conceal = false;
          break;
        }
        if (code >= 40 && code <= 47) {
          state.backgroundColor = ANSI_STANDARD_COLORS[code - 40] ?? null;
          break;
        }
        if (code >= 90 && code <= 97) {
          state.color = ANSI_BRIGHT_COLORS[code - 90] ?? null;
          state.conceal = false;
          break;
        }
        if (code >= 100 && code <= 107) {
          state.backgroundColor = ANSI_BRIGHT_COLORS[code - 100] ?? null;
          break;
        }
        if (code === 38 || code === 48) {
          const isForeground = code === 38;
          const mode = codes[i + 1];
          if (mode === 2 && codes.length >= i + 5) {
            const r = clamp(Number(codes[i + 2]));
            const g = clamp(Number(codes[i + 3]));
            const b = clamp(Number(codes[i + 4]));
            const color = rgbToHex(r, g, b);
            if (isForeground) {
              state.color = color;
              state.conceal = false;
            } else state.backgroundColor = color;
            i += 4;
            break;
          }
          if (mode === 5 && codes.length >= i + 3) {
            const palette = Number(codes[i + 2]);
            const color = Number.isFinite(palette)
              ? ansi256ToHex(palette)
              : null;
            if (color) {
              if (isForeground) {
                state.color = color;
                state.conceal = false;
              } else state.backgroundColor = color;
            }
            i += 2;
            break;
          }
        }
        break;
      }
    }
  }
}

export function ansiToHtml(raw: string): string {
  if (!raw) return '';
  const normalized = raw
    .replaceAll('\r\n', '\n')
    .replaceAll('\r', '\n')
    .replaceAll(ANSI_CSI_NON_SGR, '')
    .replaceAll(ANSI_OSC, '');

  let result = '';
  let lastIndex = 0;
  const state: AnsiStyleState = { ...defaultAnsiStyleState };
  let hasOpen = false;

  const append = (segment: string) => {
    if (!segment) return;
    result += escapeHtml(segment).replaceAll('\n', '<br/>');
  };

  let match: null | RegExpExecArray;
  while ((match = ANSI_ESCAPE_PATTERN.exec(normalized)) !== null) {
    append(normalized.slice(lastIndex, match.index));
    lastIndex = match.index + match[0].length;
    const codeText = match[1] ?? '';
    const parts = codeText.split(';').map((v) => (v === '' ? 0 : Number(v)));
    applyCodes(state, parts);
    if (hasOpen) {
      result += '</span>';
      hasOpen = false;
    }
    if (hasStyle(state)) {
      result += `<span style="${buildStyleString(state)}">`;
      hasOpen = true;
    }
  }
  append(normalized.slice(lastIndex));
  if (hasOpen) result += '</span>';
  return result;
}

export function formatBytes(size?: null | number): string {
  if (size == null || !Number.isFinite(size)) return '-';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(2)} MB`;
}

export function formatTime(value: null | string | undefined): string {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  const pad = (v: number) => String(v).padStart(2, '0');
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}:${pad(parsed.getSeconds())}`;
}

export function formatDuration(totalSeconds: number): string {
  const total = Math.max(0, Math.floor(totalSeconds));
  const hh = String(Math.floor(total / 3600)).padStart(2, '0');
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const ss = String(total % 60).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

export function normalizeList(value?: null | string | string[]): string[] {
  if (Array.isArray(value)) {
    return value.filter((item) => String(item).trim().length > 0);
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    return [value.trim()];
  }
  return [];
}
