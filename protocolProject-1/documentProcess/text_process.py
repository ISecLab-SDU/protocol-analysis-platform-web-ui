import re
import json
import os


def remove_links(text):
    return re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text)


def remove_appendix_section(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith(("Appendix", "Reference")):
            return "\n".join(lines[:i])
    return text


def extract_markdown_hierarchy(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    result = {}
    heading_stack = []  # [(level, title)]
    content_stack = []
    heading_pattern = re.compile(r'^(#{1,6})\s*(.*)')  # 支持多个空格

    def save_content():
        """保存当前 heading_stack 对应的内容到 result"""
        if heading_stack and content_stack:
            path = [remove_links(h[1]) for h in heading_stack]
            content = '\n'.join(content_stack).strip()
            if path and content:
                result[" -> ".join(path)] = remove_appendix_section(content)

    for raw_line in text.split('\n'):
        line = raw_line.replace("\xa0", " ").rstrip()
        match = heading_pattern.match(line)
        if match:
            # 新标题前保存上一个标题链的内容
            save_content()

            level = len(match.group(1))
            heading_text = match.group(2).strip()

            # 弹出比当前层级深或相等的标题
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            heading_stack.append((level, heading_text))
            content_stack = []
        else:
            content_stack.append(remove_links(line.strip()))

    # 处理最后一个标题链
    save_content()
    return result


def filter_headings_content(headings):
    filtered = {}
    started = False
    for heading, content in headings.items():
        # 识别数字编号（如"1.", "2."）或字母编号（如"A.1", "A.2"）
        if re.search(r'\b1[\.\s]|^[A-Z]\.1\b', heading):
            started = True
        if started:
            #这里原本逻辑是只有注释这一行，67，68，69行是新添加的逻辑，主要是为了过滤掉参考文献和附录这两章节
            title = re.sub(r'^[0-9A-Z.:\s\[\]]+', '', heading).strip().lower()
            # print(title)  # 注释掉以避免Windows控制台编码问题
            #if any(k in heading for k in ["References", "Appendix"]):
            if title in ("References", "Appendix"):
                break
            filtered[heading] = content
    return filtered


def clean_text(text):
    replacements = {
        "\x92": "'", "\xa0": " ", "Â": "", "â\x80\x91": "-",
        "“": "\"", "”": "\"", "\x96": "", "$": ""
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip()


def process_text(config):
    print("* Processing text content...")
    md_path = config["paths"]["markdown"]

    # 提取带标题链的内容
    headings_content = extract_markdown_hierarchy(md_path)
    filtered = filter_headings_content(headings_content)

    # 清理文本
    cleaned = {clean_text(k): clean_text(v) for k, v in filtered.items()}

    # 保存完整内容 JSON
    output_path = config["paths"]["text_processed"]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    # 保存所有标题链到 headings.json
    headings_list = list(cleaned.keys())
    with open(config["paths"]["headings"], 'w', encoding='utf-8') as f:
        json.dump(headings_list, f, ensure_ascii=False, indent=2)

    print(f"* Text processing completed\n   内容已保存到: {output_path}\n   标题链已保存到: {config['paths']['headings']}")
    return cleaned