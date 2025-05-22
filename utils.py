import os
import zipfile
import re
from typing import Union, Any, List


def dir_exists(folder_path):
    return os.path.exists(folder_path) and os.path.isdir(folder_path)


def zip_folder(folder_path, output_path):
    # 创建一个 ZipFile 对象
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 遍历文件夹中的所有文件和子文件夹
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # 获取文件的完整路径
                file_path = os.path.join(root, file)
                # 将文件添加到 zip 文件中
                zipf.write(file_path, os.path.relpath(file_path, folder_path))


def transform_string(input_str: str, macro_name, macro_replacement) -> Union[str | List[Any]]:
    # 使用正则表达式分割字符串
    pattern = rf'{{{{\s*{macro_name}\s*}}}}'
    parts = re.split(pattern, input_str)

    result = []
    for i, part in enumerate(parts):
        result.append(part)
        if i < len(parts) - 1:
            result.append(macro_replacement)

    return result if len(result) > 0 else input_str


if __name__ == "__main__":
    print(os.path.basename("gs://a/123.txt"))

    input_str = "abcde {{macro}} ghijk {{macro}} 1234"
    macro_name = "macro"
    macro_replacement = {"test": "111"}
    transformed_list = transform_string(input_str, macro_name, macro_replacement)
    print(transformed_list)

    input_str = "abcde  1234"
    macro_name = "macro"
    macro_replacement = {"test": "111"}
    transformed_list = transform_string(input_str, macro_name, macro_replacement)

    # 输出结果
    print(transformed_list)
