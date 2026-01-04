import json
import re
import pandas as pd
from pathlib import Path
import argparse

def main():
    try:
        count=0
        cnt=0
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", required=True, help="配置文件路径")
        args = parser.parse_args()
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

        protocol_chapter_file = Path(config["paths"]["paragraph_output"])
        data_file = Path(config["paths"]["final_output"])
        with open(protocol_chapter_file, "r",encoding="utf-8") as f:
            protocol_chapter = json.load(f)
        with open(data_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # 提取三个列表
        specifyKeywords = data['specify']
        modalKeywords = data['modal']
        comparativeKeywords = data['comparative']

        # **存储拆分后的结果**
        chapter_sentence_dict = {}
        for heading, content in protocol_chapter.items():
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if s.strip()]
            chapter_sentence_dict[heading] = sentences  # 存储为字

        filtered_sentences = {}
        text_output = []


        # 创建一个空的 DataFrame，用于存储句子和匹配结果
        df = pd.DataFrame(columns=["Heading", "Sentence", "Is_Matched"])

        for heading, sentences in chapter_sentence_dict.items():
            matched_sentences = []
            count+=len(sentences)
            for sentence in sentences:
                specify_matches = [word for word in specifyKeywords if word in sentence]
                modal_matches = [word for word in modalKeywords if word in sentence]
                comparative_matches = [word for word in comparativeKeywords if word in sentence]
                is_matched = False
                # 判断是否符合任意一个条件
                if len(specify_matches) >= 2 or (
                        len(specify_matches) >= 1 and (len(modal_matches) >= 1 or len(comparative_matches) >= 1)):
                    cnt+=1
                    matched_sentences.append(sentence)
                    is_matched = True
                    # 记录匹配词语信息
                    text_output.append(f"Heading: {heading}\n")
                    text_output.append(f"Sentence: {sentence}\n")
                    text_output.append(f"Matched specifyKeywords: {', '.join(specify_matches)}\n")
                    text_output.append(f"Matched modalKeywords: {', '.join(modal_matches)}\n")
                    text_output.append(f"Matched comparativeKeywords: {', '.join(comparative_matches)}\n")
                    text_output.append("-" * 50 + "\n")

                # 将结果添加到 DataFrame
                new_row = pd.DataFrame({
                        "Heading": [heading],
                        "Sentence": [sentence],
                        "Is_Matched": [is_matched]
                })
                df = pd.concat([df, new_row], ignore_index=True)

            if matched_sentences:
                filtered_sentences[heading] = matched_sentences
        
        json_path=config["paths"]["json_sentences"]
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(filtered_sentences, json_file, ensure_ascii=False, indent=4)
        txt_path=config["paths"]["txt_sentences"]
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.writelines(text_output)
        excel_path=config["paths"]["excel_sentences"]
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"总句子数：{count}")
        print(f"匹配句子数：{cnt}")

    except FileNotFoundError as e:
        print(f"关键文件缺失: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
    except Exception as e:
        print(f"未捕获错误: {str(e)}")

if __name__ == "__main__":
    main()