import json
import logging
import os
import shutil
import time
from typing import List, Dict
import re

import gradio as gr

from gcs import GCSClient
from prompt_engine import StorylinePromptEngine
from sonix import SonixClient
from utils import dir_exists
from vertexai_client import VertexaiClient
from prompts import VIDEO_URL, RELATIONSHIP, MERGED_RELATIONSHIP, STORIES, AVAILABLE_STORYLINE, GEN_STORYLINE

DEFAULT_VIDEO_DIR = "./videos"
DEFAULT_GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "online_highlight_prod")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "solar-router-391006-55ab81a8ae0e.json"
os.makedirs(DEFAULT_VIDEO_DIR, exist_ok=True)

GCS_CLIENT = GCSClient()
SONIX_CLIENT = SonixClient("HwD0K6mdKV1xOpvlQtrUIQtt")
VAI_CLIENT = VertexaiClient(
    "solar-router-391006", "asia-east1", None)

# 生成配置
GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0.5,
    "top_p": 0.95,
}


class ExtractorState:
    is_upload_video: bool = False
    episodes_name: str = ""
    episodes_full_path: str = ""
    gcs_folder: str = ""
    gcs_urls: Dict = {}
    sign_urls: List[tuple[str, str]] = []
    scripts: Dict = {}
    relationships: str = ""
    merged_relationships: str = ""
    stories: str = ""
    available_storylines: str = ""
    storyline: str = ""
    config: Dict = {}


def _select_video(exist_video, gr_state):
    is_upload_video = exist_video == 0
    gr_state.is_upload_video = is_upload_video

    return [gr.Textbox(visible=not is_upload_video),
            gr.Textbox(visible=is_upload_video),
            gr.File(visible=is_upload_video)]


def _upload_videos(episodes_name, files, gr_state):
    video_full_path = f"{DEFAULT_VIDEO_DIR}/{episodes_name}"
    logging.info(f"上传视频文件上传至：{video_full_path}")

    if dir_exists(video_full_path):
        shutil.rmtree(video_full_path)
    os.makedirs(video_full_path, exist_ok=True)

    for file_path in filter(lambda f: f.lower().endswith('.mp4'), files):
        base_name = os.path.basename(file_path)
        dest_path = os.path.join(video_full_path, base_name)
        # 将文件从临时目录复制到目标目录
        shutil.copy(file_path, dest_path)

    gr_state.episodes_name = episodes_name
    gr_state.episodes_full_path = video_full_path


def _extract_script(videos_path, gr_state):
    # TODO 字幕生成可以添加缓存，加快生成速度

    bucket = DEFAULT_GCS_BUCKET

    if gr_state.is_upload_video:
        # 上传文件至GCS
        logging.info(f"上传视频文件：{gr_state.episodes_full_path} 至 gcs：{bucket}")
        blobs = GCS_CLIENT.upload_directory_to_gcs(gr_state.episodes_full_path, bucket)
    else:
        bucket = GCS_CLIENT.extract_bucket(videos_path)
        folder = GCSClient.extract_gcs_path(videos_path)
        gr_state.episodes_name = folder
        logging.info(f"获取剧集《{folder}》视频文件列表.")
        blobs = GCS_CLIENT.list_gcs_blobs(bucket, folder, [".mp4"])

    gr_state.gcs_urls = {b: f"gs://{bucket}/{b}" for b in blobs}

    # 生成临时访问链接
    logging.info(f"生成剧集《{gr_state.episodes_name}》视频文件签名地址.")
    gr_state.sign_urls = [GCS_CLIENT.get_gcs_sign_url(bucket, blob, 24) for blob in blobs]

    # 创建 sonix 文件夹
    sonix_folder = SONIX_CLIENT.get_folder(gr_state.episodes_name)
    if sonix_folder is None:
        sonix_folder = SONIX_CLIENT.new_folder(gr_state.episodes_name)

    # 上传视频文件
    logging.info(f"开始将剧集《{gr_state.episodes_name}》视频上传至 Sonix...")
    upload_sonix_videos = []
    for f in gr_state.sign_urls:
        # 已存在的视频不在上传，节约空间
        media = SONIX_CLIENT.list_media(search=f[0])
        if media and media.get("media") and len(media.get("media")) > 0:
            upload_sonix_videos.append(media.get("media")[0])
        else:
            upload_sonix_videos.append(SONIX_CLIENT.upload_media(sonix_folder.get("id"), f))

    # 检查视频文件上传状态
    logging.info(f"检查剧集《{gr_state.episodes_name}》视频上传 Sonix 状态...")
    upload_completed_videos = []
    end_states = ["completed", "blocked", "failed", "duplicate"]
    while len(upload_completed_videos) < len(upload_sonix_videos):
        time.sleep(5)

        for v in filter(lambda iv: iv.get("id") not in upload_completed_videos, upload_sonix_videos):
            media_status = SONIX_CLIENT.get_media_status(v.get("id"))
            logging.info(f"剧集《{gr_state.episodes_name}》视频上传至 Sonix 状态： {media_status}")
            if media_status.get("status") in end_states:
                if media_status.get("status") == "duplicate":
                    v["id"] = media_status.get("duplicate_media_id")
                    upload_completed_videos.append(media_status.get("duplicate_media_id"))
                else:
                    upload_completed_videos.append(media_status.get("id"))

    # 获取字幕内容
    logging.info(f"获取剧集《{gr_state.episodes_name}》视频字幕信息...")
    transcripts = {}
    for v in upload_sonix_videos:
        transcripts[v.get("name")] = SONIX_CLIENT.get_text_transcript(v.get("id"))

    gr_state.scripts = transcripts

    return json.dumps(transcripts, ensure_ascii=False, indent=4)


def _update_storyline_config(batch_size, llm_model, max_output_tokens, temperature, top_p, global_state):
    global_state.config["batch_size"] = int(batch_size)
    global_state.config["llm_model"] = llm_model
    global_state.config["max_output_tokens"] = int(max_output_tokens)
    global_state.config["temperature"] = float(temperature)
    global_state.config["top_p"] = float(top_p)


def _build_generation_config(global_state):
    return {
        "max_output_tokens": global_state.config["max_output_tokens"],
        "temperature": global_state.config["temperature"],
        "top_p": global_state.config["top_p"],
    }


def _fill_gcs_infos(global_state):
    if global_state.gcs_urls is None or len(global_state.gcs_urls) == 0:
        bucket = GCS_CLIENT.extract_bucket(global_state.gcs_folder)
        folder = GCSClient.extract_gcs_path(global_state.gcs_folder)
        global_state.episodes_name = folder
        logging.info(f"获取剧集《{folder}》视频文件列表.")
        blobs = GCS_CLIENT.list_gcs_blobs(bucket, folder, [".mp4"])

        global_state.gcs_urls = {b: f"gs://{bucket}/{b}" for b in blobs}


def _analyze_relationships(batch_size, llm_model, max_output_tokens, temperature, top_p,
                           prompt_template, global_state):
    batch_size = int(batch_size)
    _fill_gcs_infos(global_state)
    _update_storyline_config(batch_size, llm_model, max_output_tokens, temperature, top_p, global_state)
    generation_config = _build_generation_config(global_state)
    prompt_engine = StorylinePromptEngine(global_state.scripts, global_state.gcs_urls)

    relationships = []
    logging.info(f"开始批量分析人物关系，批大小：{batch_size}， 总集数： {len(global_state.gcs_urls)}")
    prompt_tokens = 0
    response_tokens = 0
    for i in range(0, len(global_state.scripts), batch_size):
        logging.info(f"批量分析人物关系，第 {(i+1)//batch_size} 批")
        prompt = prompt_engine.render(prompt_template, i//batch_size, batch_size)
        response = VAI_CLIENT.chat(llm_model, prompt, generation_config)
        input_tokens = int(re.search(r'prompt_token_count:\s*(\d+)', str(response)).group(1))
        output_tokens = int(re.search(r'candidates_token_count:\s*(\d+)', str(response)).group(1))
        relationships.append(response)
        prompt_tokens += input_tokens
        response_tokens += output_tokens
    token_usage = f"输入tokens：{prompt_tokens}    输出tokens：{response_tokens}"
    global_state.relationships = "\n".join([s.text for s in relationships])

    return global_state.relationships, token_usage


def _merge_relationships(batch_size, llm_model, max_output_tokens, temperature, top_p,
                         prompt_template, global_state):
    _fill_gcs_infos(global_state)
    _update_storyline_config(batch_size, llm_model, max_output_tokens, temperature, top_p, global_state)
    generation_config = _build_generation_config(global_state)
    prompt_engine = StorylinePromptEngine(
        global_state.scripts,
        global_state.gcs_urls,
        global_state.relationships
    )

    logging.info(f"开始合并人物关系...")
    prompt = prompt_engine.render(prompt_template, -1)
    response = VAI_CLIENT.chat(llm_model, prompt, generation_config)
    prompt_tokens = int(re.search(r'prompt_token_count:\s*(\d+)', str(response)).group(1))
    response_tokens = int(re.search(r'candidates_token_count:\s*(\d+)', str(response)).group(1))
    logging.info({f"结果是：{response}"})
    global_state.merged_relationships = response.text
    token_usage = f"输入tokens：{prompt_tokens}    输出tokens：{response_tokens}"

    return global_state.merged_relationships, token_usage


def _extract_story(batch_size, llm_model, max_output_tokens, temperature, top_p,
                   prompt_template, global_state):
    batch_size = int(batch_size)
    _fill_gcs_infos(global_state)
    _update_storyline_config(batch_size, llm_model, max_output_tokens, temperature, top_p, global_state)
    generation_config = _build_generation_config(global_state)
    prompt_engine = StorylinePromptEngine(
        global_state.scripts,
        global_state.gcs_urls,
        global_state.relationships,
        merged_relationships=global_state.merged_relationships
    )

    stories = []
    logging.info(f"开始批量提取分集剧情，批大小：{batch_size}， 总集数： {len(global_state.gcs_urls)}")
    prompt_tokens = 0
    response_tokens = 0 
    for i in range(0, len(global_state.scripts), batch_size):
        logging.info(f"批量提取分集剧情，第 {(i + 1)//batch_size} 批")
        prompt = prompt_engine.render(prompt_template, i//batch_size, batch_size)
        logging.info(f"分集剧情Prompt: {prompt}")
        response = VAI_CLIENT.chat(llm_model, prompt, generation_config)
        input_tokens = int(re.search(r'prompt_token_count:\s*(\d+)', str(response)).group(1))
        output_tokens = int(re.search(r'candidates_token_count:\s*(\d+)', str(response)).group(1)) 
        stories.append(response)
        prompt_tokens += input_tokens
        response_tokens += output_tokens
    global_state.stories = "*********************\n".join([s.text for s in stories])
    token_usage = f"输入tokens：{prompt_tokens}    输出tokens：{response_tokens}"

    return global_state.stories, token_usage


def _select_storylines(batch_size, llm_model, max_output_tokens, temperature, top_p,
                       prompt_template, global_state):
    _fill_gcs_infos(global_state)
    _update_storyline_config(batch_size, llm_model, max_output_tokens, temperature, top_p, global_state)
    generation_config = _build_generation_config(global_state)
    prompt_engine = StorylinePromptEngine(
        global_state.scripts,
        global_state.gcs_urls,
        global_state.relationships,
        global_state.stories,
        global_state.merged_relationships
    )

    logging.info(f"开始筛选可用高光故事线...")
    prompt = prompt_engine.render(prompt_template, -1)
    response = VAI_CLIENT.chat(llm_model, prompt, generation_config)
    global_state.available_storylines = response.text
    prompt_tokens = int(re.search(r'prompt_token_count:\s*(\d+)', str(response)).group(1))
    response_tokens = int(re.search(r'candidates_token_count:\s*(\d+)', str(response)).group(1))
    # 把两个花括号中间的空格去掉，防止影响渲染
    global_state.available_storylines = re.sub(r'{{\s*(.*?)\s*}}', r'{{\1}}', global_state.available_storylines)
    token_usage = f"输入tokens：{prompt_tokens}    输出tokens：{response_tokens}"

    return global_state.available_storylines, token_usage


def _generate_storyline(batch_size, llm_model, max_output_tokens, temperature, top_p,
                        prompt_template, global_state):
    _fill_gcs_infos(global_state)
    _update_storyline_config(batch_size, llm_model, max_output_tokens, temperature, top_p, global_state)
    generation_config = _build_generation_config(global_state)
    prompt_engine = StorylinePromptEngine(
        global_state.scripts,
        global_state.gcs_urls,
        global_state.relationships,
        global_state.stories,
        global_state.merged_relationships,
        global_state.available_storylines
    )

    logging.info(f"开始生成故事线...")
    prompt = prompt_engine.render(prompt_template, -1)
    response = VAI_CLIENT.chat(llm_model, prompt, generation_config)
    prompt_tokens = int(re.search(r'prompt_token_count:\s*(\d+)', str(response)).group(1))
    response_tokens = int(re.search(r'candidates_token_count:\s*(\d+)', str(response)).group(1))
    global_state.storyline = response.text
    token_usage = f"输入tokens：{prompt_tokens}    输出tokens：{response_tokens}"
    
    return global_state.storyline, token_usage


def _state_change(item, global_state, comp: gr.Component):
    if comp.key.startswith("config:"):
        global_state.config[comp.key[7:]] = item
    else:
        if isinstance(getattr(ExtractorState(), comp.key, None), Dict):
            setattr(global_state, comp.key, json.loads(item))
        else:
            setattr(global_state, comp.key, item)


def create_storyline_extractor_interface():
    with gr.Blocks() as extractor:
        gr.Markdown("# 短剧故事线提取")
        gr.Markdown("## 使用说明")
        gr.Markdown("### 视频文件命名规则")
        gr.Markdown("* {集数}.mp4，如： 1.mp4, 2.mp4")
        gr.Markdown("### prompt 支持的宏列表:")
        gr.Markdown("* 剧集视频地址： {{videos}}")
        gr.Markdown("* 对话字幕： {{scripts}}")
        gr.Markdown("* 分批人物关系： {{relationships}}")
        gr.Markdown("* 合并人物关系： {{merged_relationships}}")
        gr.Markdown("* 分集剧情： {{stories}}")
        gr.Markdown("* 高光情节分类定义： {{storyline_definition}}")
        gr.Markdown("* 可选高光故事线+定义+生成方式： {{available_storylines}}")
        gr.Markdown("* 起始剧集： {{start_ep}}")
        gr.Markdown("* 终止剧集： {{end_ep}}")
        gr.Markdown("* 剧集数量： {{num_ep}}")  

        global_state = gr.State(ExtractorState())

        exist_video = gr.Radio(
            choices=[("上传新的视频文件", 0), ("选择已有文件", 1)],
            label="选择视频类型")

        videos_path = gr.Textbox(label="输入 google could storage 视频文件夹：", visible=False, key="gcs_folder", value=VIDEO_URL)
        upload_episodes_name = gr.Textbox(label="输入剧集名称：", visible=False)
        upload_episodes = gr.File(
            label="上传视频文件", file_count="multiple", file_types=[".mp4"], visible=False, interactive=True)

        exist_video.change(
            fn=_select_video,
            inputs=[exist_video, global_state],
            outputs=[videos_path, upload_episodes_name, upload_episodes]
        )

        gr.Markdown("## 获取对话字幕信息")
        extract_script_button = gr.Button("提取视频对话信息")
        extract_scripts = gr.TextArea(label="对话信息：", key="scripts", interactive=True)

        extract_script_button.click(
            fn=_extract_script,
            inputs=[videos_path, global_state],
            outputs=extract_scripts
        )
        upload_episodes.upload(
            fn=_upload_videos,
            inputs=[upload_episodes_name, upload_episodes, global_state]
        )

        gr.Markdown("## 短剧故事线生成")
        gr.Markdown("### 故事线生成设置")
        with gr.Row():
            videos_batch_size = gr.Textbox(label="短剧批量集数", value="5", key="config:batch_size")
            llm_model = gr.Dropdown(label="选择模型", choices=["gemini-1.5-pro-002", "gemini-2.0-flash-001"],
                                    key="config:llm_model")
            max_output_tokens = gr.Textbox(label="最大生成tokens数", value="8192", key="max_output_tokens")
            temperature = gr.Textbox(label="temperature", value="0.5", key="config:temperature")
            top_p = gr.Textbox(label="top_p", value="0.95", key="config:top_p")

        gr.Markdown("### step1: 分析人物关系")
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### step1.1: 分集分析人物关系")
                analyze_relationships_prompt = gr.TextArea(label="分析人物关系prompt", value=RELATIONSHIP)
                relationships = gr.TextArea(label="人物关系信息", key="relationships")
                token_usage = gr.Textbox(label="消耗 Token 数", interactive=False)
                analyze_relationships_button = gr.Button("分析人物关系")

                analyze_relationships_button.click(
                    fn=_analyze_relationships,
                    inputs=[videos_batch_size, llm_model, max_output_tokens, temperature, top_p,
                            analyze_relationships_prompt, global_state],
                    outputs=[relationships, token_usage]
                )

            with gr.Column():
                gr.Markdown("#### step1.2: 合并人物关系")
                merge_relationships_prompt = gr.TextArea(label="合并人物关系prompt", value=MERGED_RELATIONSHIP)
                merged_relationships = gr.TextArea(label="人物关系信息", key="merged_relationships")
                token_usage = gr.Textbox(label="消耗 Token 数", interactive=False)
                merge_relationships_button = gr.Button("合并人物关系")

                merge_relationships_button.click(
                    fn=_merge_relationships,
                    inputs=[videos_batch_size, llm_model, max_output_tokens, temperature, top_p,
                            merge_relationships_prompt, global_state],
                    outputs=[merged_relationships, token_usage]
                )

        with gr.Column():
            gr.Markdown("### step2: 提取分集剧情")
            extract_story_prompt = gr.TextArea(label="分集剧情提取Prompt", value=STORIES)
            stories = gr.TextArea(label="分集剧情信息", key="stories")
            token_usage = gr.Textbox(label="消耗 Token 数", interactive=False)
            extract_button = gr.Button("提取分集剧情")
            extract_button.click(
                fn=_extract_story,
                inputs=[videos_batch_size, llm_model, max_output_tokens, temperature, top_p,
                        extract_story_prompt, global_state],
                outputs=[stories, token_usage]
            )

        with gr.Column():
            gr.Markdown("### step3: 筛选可用高光故事线")
            select_storylines_prompt = gr.TextArea(label="可用高光故事线Prompt", value=AVAILABLE_STORYLINE)
            available_storylines = gr.TextArea(label="分集剧情信息", key="available_storylines")
            token_usage = gr.Textbox(label="消耗 Token 数", interactive=False)
            select_storylines_button = gr.Button("筛选高光故事线")
            select_storylines_button.click(
                fn=_select_storylines,
                inputs=[videos_batch_size, llm_model, max_output_tokens, temperature, top_p,
                        select_storylines_prompt, global_state],
                outputs=[available_storylines, token_usage]
            )

        with gr.Column():
            gr.Markdown("### step4: 生成故事线")
            generate_storyline_prompt = gr.TextArea(label="故事线生成Prompt", value=GEN_STORYLINE)
            generate_storylines = gr.TextArea(label="故事线信息")
            token_usage = gr.Textbox(label="消耗 Token 数", interactive=False)
            generate_storyline_button = gr.Button("生成故事线")
            generate_storyline_button.click(
                fn=_generate_storyline,
                inputs=[videos_batch_size, llm_model, max_output_tokens, temperature, top_p,
                        generate_storyline_prompt, global_state],
                outputs=[generate_storylines, token_usage]
            )

        for item in [videos_path, extract_scripts, videos_batch_size, llm_model, max_output_tokens, temperature, top_p,
                     relationships, merged_relationships, stories, available_storylines]:
            item.change(
                fn=lambda i, g, c=item: _state_change(i, g, c),
                inputs=[item, global_state])

        return extractor


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = create_storyline_extractor_interface()
    app.launch(server_name="0.0.0.0", server_port=7861)
