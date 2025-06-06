import json
import re
import xlsxwriter
import argparse
import os


def extract_episode_timestamp(text):
    """
    从文本中提取集数和时间戳信息
    """
    match = re.search(r'(第\d+集)：(\[.*?\]-\[.*?\])', text)
    if match:
        return match.group(1), match.group(2)
    return '第0集', '00:00:00'


def process_json_data(json_data):
    """
    处理 JSON 数据，将每个故事按时间戳拆分并整理成表格数据
    """
    all_data = []
    for item in json_data:
        story_name_key = [key for key in item.keys() if "故事" in key][0]
        story_name = item[story_name_key]
        merged_episodes = item["合并集数"]
        main_characters = ", ".join(item["主要人物"])
        reason = item["符合原因"]

        for event_type in ['起因', '冲突', '反转', '结局']:
            parts = re.findall(r'\(.*?\)', item[event_type])
            for i in range(len(parts)):
                episode, timestamp = extract_episode_timestamp(parts[i])
                story_process = event_type
                if i < len(parts) - 1:
                    next_part_start = item[event_type].find(parts[i + 1])
                    story_plot = item[event_type][item[event_type].find(parts[i]) + len(parts[i]):next_part_start].strip()
                else:
                    story_plot = item[event_type][item[event_type].find(parts[i]) + len(parts[i]):].strip()
                all_data.append([
                    story_name, merged_episodes, main_characters,
                    reason, episode, timestamp, story_process, story_plot
                ])
    return all_data


def write_to_excel(all_processed_data, output_file, json_file_names):
    """
    将整理好的数据写入 Excel 文件，每个 JSON 文件的数据写入一个单独的 sheet
    """
    workbook = xlsxwriter.Workbook(output_file)

    for i, data in enumerate(all_processed_data):
        sheet_name = os.path.splitext(os.path.basename(json_file_names[i]))[0]
        worksheet = workbook.add_worksheet(sheet_name)

        headers = ["故事名称", "合并集数", "主要人物", "符合原因", "集数", "时间戳", "故事过程", "故事剧情"]
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header)

        row = 1
        last_story_name = None
        start_row = 1
        for row_data in data:
            if row_data[0]!= last_story_name and last_story_name is not None:
                for col in range(4):
                    worksheet.merge_range(start_row, col, row - 1, col, data[start_row - 1][col])
                start_row = row

            for col_num, value in enumerate(row_data):
                worksheet.write(row, col_num, value)

            row += 1
            last_story_name = row_data[0]

        if last_story_name is not None:
            for col in range(4):
                worksheet.merge_range(start_row, col, row - 1, col, data[start_row - 1][col])

    workbook.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process multiple JSON data and write to Excel')
    parser.add_argument('json_files', type=str, nargs='+', help='Paths to the JSON files, separated by space')
    parser.add_argument('output_file', type=str, help='Path to the output Excel file')
    args = parser.parse_args()

    all_processed_data = []
    json_file_names = []
    for json_file in args.json_files:
        json_file_names.append(json_file)
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            processed_data = process_json_data(json_data)
            all_processed_data.append(processed_data)

    write_to_excel(all_processed_data, args.output_file, json_file_names)