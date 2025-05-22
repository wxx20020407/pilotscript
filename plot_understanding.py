import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import gradio as gr
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting

# 常量定义
DEFAULT_EXTRACT_PATH = "./shots"
DEFAULT_PROJECT = "solar-router-391006"
DEFAULT_LOCATION = "us-central1"
DEFAULT_API_ENDPOINT = "us-central1-aiplatform.googleapis.com"
DEFAULT_MODEL = "gemini-1.5-pro-002"

# 安全设置
SAFETY_SETTINGS = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
]

# 生成配置
GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0.5,
    "top_p": 0.95,
}

# 提示模板
PROMPT_TEMPLATE = """的对话文本，其中角色以代号称呼。请按以下要求完成任务：
##角色命名匹配：为对话中的每个代号和角色进行匹配，为无重复、无遗漏的双向映射关系，切勿随意命名。若无法匹配，根据外貌特征描述角色，或直接称为神秘人。可以通过对话间的称呼命名角色。请在内容开头明确告知匹配结果。
##分集剧情转述：
-确保从视频开头至结尾完整转述，无任何遗漏。
-切记所有转述按照镜头顺序，切勿提前或滞后
-人物登场时，若有文字介绍，一并转述。
-可通过对话间的称呼获取人物信息
-对于未知人物，详细描述其样貌；若无法识别角色，使用合适代称，如神秘人、黑人男子、西装男子、白衣女子等，切勿随意分配名称。
-仅转述视频中出现的动作，不要联想。分不清动作的发出者时，仅描述出现的物体或声音
-只输出本集剧情，但其他剧集可作为知识记忆并学习
##思考要点：
场景描述：清晰阐述人物在何时、何地发生后续事件。
人物描绘：明确指出场景中出现的人物及其身份、特征。
台词记录：记录角色所说的话，并描述其说话时的动作、神情和语气。
行为记录：详细描述角色的动作，包括无对话时的眼神暗示、动作暗示、对视、点头示意、挥手等重要动作。
镜头暗示：若物品变动引发所有人的其他反应，需描述该变动事件，这通常是重要的转折节点。
场景转换：当剧情结束并转换地点时，提示 "镜头一转"，然后按照上述流程重新描述新剧情。"""


class PlotGenerator:
    """短剧剧情生成器类"""
    
    def __init__(self, project: str = DEFAULT_PROJECT, location: str = DEFAULT_LOCATION, 
                 api_endpoint: str = DEFAULT_API_ENDPOINT, model_name: str = DEFAULT_MODEL):
        """初始化短剧剧情生成器
        
        Args:
            project: GCP项目ID
            location: API地区
            api_endpoint: API端点
            model_name: 模型名称
        """
        self.project = project
        self.location = location
        self.api_endpoint = api_endpoint
        self.model_name = model_name
        self._initialize_vertexai()
        self.model = GenerativeModel(model_name)
    
    def _initialize_vertexai(self) -> None:
        """初始化Vertex AI配置"""
        vertexai.init(
            project=self.project,
            location=self.location,
            api_endpoint=self.api_endpoint
        )
    
    def generate_single_plot(self, prompt: str, shots: str, video_full_path: str) -> str:
        """生成单个剧集的剧情概要
        
        Args:
            prompt: 用户提供的提示词
            shots: 字幕文本
            video_full_path: 视频完整路径
            
        Returns:
            str: 生成的剧情概要
        """
        # 创建文本和视频部分
        shot_part = Part.from_data(
            mime_type="text/plain",
            data=shots.encode('utf-8'),
        )
        video_part = Part.from_uri(
            mime_type="video/mp4",
            uri=video_full_path,
        )
        
        # 构建完整提示
        full_prompt = [
            "任务说明\n你是一位专业的短剧剪辑师，需根据视频内容进行剧情转述。现有文件", 
            shot_part, 
            "，它是视频", 
            video_part, 
            prompt
        ]
        
        # 生成内容
        responses = self.model.generate_content(
            full_prompt,
            generation_config=GENERATION_CONFIG,
            safety_settings=SAFETY_SETTINGS,
            stream=True,
        )
        
        # 收集响应
        plot = ""
        for response in responses:
            plot += response.text
        
        return plot
    
    def generate_batch_plots(self, video_path: str, prompt: str, 
                             extract_path: str = DEFAULT_EXTRACT_PATH) -> str:
        """批量生成多个剧集的剧情概要
        
        Args:
            video_path: 视频文件目录路径
            prompt: 用户提供的提示词
            extract_path: 解压字幕文件的路径
            
        Returns:
            str: 所有剧集的剧情概要
        """
        result = []
        extract_dir = Path(extract_path)
        
        # 确保提示词包含模板内容
        if not prompt.endswith(PROMPT_TEMPLATE):
            prompt += PROMPT_TEMPLATE
        
        # 处理每个字幕文件
        for file_path in sorted(
                [f for f in extract_dir.glob("*.txt")], 
                key=lambda n: int(n.stem)):
            
            # 读取字幕内容
            with open(file_path, "r", encoding="utf-8") as f:
                shots = f.read()
            
            # 构建视频路径
            episode_num = file_path.stem
            video_full_path = f"{video_path}/{episode_num}.mp4"
            
            # 生成剧情并添加到结果
            plot = self.generate_single_plot(prompt, shots, video_full_path)
            result.append(f"第{episode_num}集剧情\n{plot}\n\n")
        
        return "\n".join(result)


def unzip_shots(file) -> Optional[str]:
    """解压字幕文件包
    
    Args:
        file: 上传的zip文件
        
    Returns:
        Optional[str]: 解压后的文件列表信息，如果失败则返回None
    """
    if file is None:
        return None

    extract_dir = Path(DEFAULT_EXTRACT_PATH)
    extract_dir.mkdir(exist_ok=True)

    try:
        with zipfile.ZipFile(file.name, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        files = list(extract_dir.glob("*.txt"))
        return f"字幕文件: {[f.name for f in files]}"
    except Exception as e:
        return f"解压失败: {str(e)}"


def clear_all() -> Tuple[None, ...]:
    """清空所有输入和输出"""
    return (None, None, None, None)


@dataclass
class PlotUIComponents:
    """存储剧情生成器UI组件的数据类"""
    file_input: Optional[gr.File] = None
    display_files: Optional[gr.Textbox] = None
    video_path: Optional[gr.Textbox] = None
    prompt: Optional[gr.Textbox] = None
    result: Optional[gr.TextArea] = None
    
    def get_input_components(self) -> List:
        """获取输入组件列表"""
        return [self.video_path, self.prompt]
    
    def get_output_components(self) -> List:
        """获取输出组件列表"""
        return [self.result]
    
    def get_clear_components(self) -> List:
        """获取需要清除的组件列表"""
        return [self.file_input, self.result, self.video_path, self.prompt]


class PlotUIEventHandler:
    """剧情生成器UI事件处理器，负责处理所有UI事件"""
    
    @staticmethod
    def handle_submit(video_path: str, prompt: str) -> str:
        """处理提交按钮点击事件
        
        Args:
            video_path: 视频路径
            prompt: 提示词
            
        Returns:
            str: 生成的剧情概要
        """
        generator = PlotGenerator()
        return generator.generate_batch_plots(video_path, prompt)
    
    @staticmethod
    def handle_file_upload(file) -> str:
        """处理文件上传事件
        
        Args:
            file: 上传的文件
            
        Returns:
            str: 解压结果信息
        """
        return unzip_shots(file)
    
    @staticmethod
    def handle_clear() -> Tuple[None, ...]:
        """处理清除按钮点击事件
        
        Returns:
            Tuple[None, ...]: 用于清除UI组件的值
        """
        return clear_all()


def create_plot_interface() -> gr.Blocks:
    """创建Gradio界面"""
    # 创建UI组件容器
    ui = PlotUIComponents()
    
    with gr.Blocks() as plot_tool:
        gr.HTML("<title>短剧剧集理解</title>")
        gr.Markdown("# 短剧剧集理解")

        with gr.Column():
            file_input = gr.File(label="上传短剧剧集字幕 zip 包", file_types=[".zip"], height=120)
            display_files = gr.Textbox(label="字幕文件列表")
            ui.file_input = file_input  # 存储引用
            ui.display_files = display_files

        video_path = gr.Textbox(
            label="Google云上的视频文件目录地址", 
            value="gs://online_highlight_prod/黑暗中的爱"
        )
        prompt = gr.Textbox(label="剧情理解prompt")
        ui.video_path = video_path
        ui.prompt = prompt
        
        # 设置文件上传事件
        file_input.change(
            fn=PlotUIEventHandler.handle_file_upload, 
            inputs=file_input,
            outputs=display_files
        )
        
        with gr.Row():
            result = gr.TextArea(label="剧情概要")
            ui.result = result

        with gr.Row():
            submit_button = gr.Button("提交")
            clear_button = gr.Button("清空")

        # 设置按钮事件，使用原始组件，而不是通过ui对象引用
        submit_button.click(
            fn=PlotUIEventHandler.handle_submit,
            inputs=[video_path, prompt],
            outputs=result
        )
        
        clear_button.click(
            fn=PlotUIEventHandler.handle_clear,
            inputs=None, 
            outputs=[file_input, result, video_path, prompt]  # 直接使用组件引用
        )

        return plot_tool


if __name__ == "__main__":
    app = create_plot_interface()
    app.launch(server_name="0.0.0.0", server_port=7861)
