import html2text
from lxml import html
import re
import os
import json


def extract_and_save_tables(html_path, output_json_path):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        tree = html.fromstring(f.read())

    tables_data = []
    for i, table in enumerate(tree.xpath("//table"), start=1):
        # ---- 获取表格标题（向上找最近的段落或标题标签）----
        title = ""
        prev = table.getprevious()
        while prev is not None:
            if prev.tag in ["p", "h1", "h2", "h3", "h4", "h5", "h6"]:
                title = " ".join(prev.text_content().split())
                break
            prev = prev.getprevious()

        # ---- 解析表格 ----
        rows_data = []
        for row in table.xpath(".//tr"):
            row_data = []
            for cell in row.xpath(".//th|.//td"):
                text = " ".join(cell.text_content().split())
                colspan = int(cell.attrib.get("colspan", 1))
                rowspan = int(cell.attrib.get("rowspan", 1))
                row_data.append({
                    "text": text,
                    "colspan": colspan,
                    "rowspan": rowspan
                })
            if row_data:
                rows_data.append(row_data)

        tables_data.append({
            "title": title,
            "rows": rows_data
        })

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(tables_data, f, ensure_ascii=False, indent=2)


def clean_rfc_html(file_path, output_path, tables_json_path):
    # 1. 先提取表格
    extract_and_save_tables(file_path, tables_json_path)

    # 2. 读取 HTML 并删除表格
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # 删除所有表格标签及内容
    content = re.sub(r"<table.*?</table>", "", content, flags=re.DOTALL | re.IGNORECASE)
    tree = html.fromstring(content)

    # 清理页眉页脚
    for element in tree.xpath("//span[contains(@class, 'grey')]"):
        parent = element.getparent()
        if element.tail:
            previous = element.getprevious()
            if previous is not None:
                previous.tail = (previous.tail or "") + element.tail
            else:
                parent.text = (parent.text or "") + element.tail
        parent.remove(element)

    # 清理换行标签
    for element in tree.xpath("//br | //hr"):
        element.getparent().remove(element)

    # 处理分页符
    for element in tree.xpath("//pre[@class='newpage']"):
        parent = element.getparent()
        if element.text:
            parent.text = (parent.text or "") + element.text
        for child in element:
            parent.append(child)
        if element.tail:
            previous = element.getprevious()
            if previous is not None:
                previous.tail = (previous.tail or "") + element.tail
            else:
                parent.text = (parent.text or "") + element.tail
        parent.remove(element)

    # 删除注释
    for comment in tree.xpath('//comment()'):
        parent = comment.getparent()
        if parent is not None:
            parent.remove(comment)

    # 保存清理后的HTML
    cleaned_html = html.tostring(tree, encoding='unicode', pretty_print=True)
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(cleaned_html)


def html_to_markdown(file_path, output_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = html.parse(file)

    # 转换标题标签
    for span in tree.xpath('//span[starts-with(@class, "h")]'):
        class_name = span.get('class')
        if class_name and class_name[1:].isdigit():
            new_tag = html.Element(f'h{class_name[1:]}')
            for child in span.iterchildren():
                new_tag.append(child)
            if span.tail:
                new_tag.tail = span.tail.strip()
            span.getparent().replace(span, new_tag)

    # 转换HTML到Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    markdown = h.handle(html.tostring(tree, encoding='unicode'))
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)


def process_html(config):
    print("* Processing HTML document...")
    clean_rfc_html(
        config["paths"]["html_input"],
        config["paths"]["cleaned_html"],
        config["paths"]["tables"]
    )
    html_to_markdown(config["paths"]["cleaned_html"], config["paths"]["markdown"])
    print("* HTML processing completed")