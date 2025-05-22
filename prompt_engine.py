import json
import logging
import os.path
import re
from typing import Any, Dict, List, Union

from jinja2 import Environment, Undefined, Template
from vertexai.generative_models import Part, Content


def _transform_to_content(prompt: str, videos: List[str]) -> Union[str | List[Content]]:
    # 富媒体类型需要特殊处理: video, image 等
    # 处理Video
    pattern = r'{{\s*videos\s*}}'
    parts = re.split(pattern, prompt)

    if parts and len(parts) > 0:
        form_parts = []
        for i, part in enumerate(parts):
            if len(part) > 0:
                form_parts.append(Part.from_text(text=part))
            if i < len(parts) - 1:
                form_parts.extend([Part.from_uri(mime_type="video/mp4", uri=v) for v in videos])
        return [Content(role="user", parts=form_parts)]
    else:
        return prompt

class KeepMacroUndefined(Undefined):
        def __str__(self):
            # 让未定义变量保持原始的 Jinja2 语法，不会被渲染
            return f"{{{{ {self._undefined_name} }}}}"

class StorylinePromptEngine:

    def __init__(self,
                 scripts: Dict[str, Any],
                 videos: Dict[str, Any],
                 relationships: Any = "",
                 stories: Union[Dict[str, Any], str] = "",
                 merged_relationships: str = "",
                 available_storylines: str = "",
                 storyline_definition_path: str = "storyline_definition.json",
                 storyline_def_detailed_path: str = "storyline_def_detailed.json",
                 storyline_generation_path: str = "storyline_generation.json"):
        self.scripts = StorylinePromptEngine._get_sorted_list(scripts)
        if isinstance(stories, Dict):
            self.stories = StorylinePromptEngine._get_sorted_list(stories)
        else:
            self.stories = stories

        self.videos = StorylinePromptEngine._get_sorted_list(videos)
        self.relationships = json.dumps(relationships, ensure_ascii=False, indent=4)
        self.merge_relationships = merged_relationships
        self.available_storylines = available_storylines

        self.storyline_definition = self._load_json(storyline_definition_path)

        self.storyline_def_detailed = self._load_json(storyline_def_detailed_path)

        self.storyline_generation = self._load_json(storyline_generation_path)

    @staticmethod
    def _load_json(file_path: str) -> Dict:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return{}
    
    @staticmethod
    def _sorted_key(blob_name):
        basename = os.path.basename(blob_name)
        match = re.search(r'\d+', basename)
        if match:
            return int(match.group())
        return 0

    @staticmethod
    def _get_sorted_list(values: Dict[str, Any]) -> List[Any]:
        return [values.get(key) for key in sorted(values.keys(), key=StorylinePromptEngine._sorted_key)]
    
    def _apply_storyline_generation(self, prompt: str) -> str:
        for key in re.findall(r"{{(.*?)}}", self.available_storylines):
            if key in self.storyline_def_detailed and key in self.storyline_generation:
                detailed_def = json.dumps(self.storyline_def_detailed[key], ensure_ascii=False, indent=4)
                generation_steps = json.dumps(self.storyline_generation[key], ensure_ascii=False, indent=4)
                prompt = prompt.replace(f"{{{{{key}}}}}", f"高光情节：{{{{{key}}}}}\n详细定义: {detailed_def}\n故事生成方式: {generation_steps}")

        return prompt

    def render(self, prompt: str, round_num: int, round_size: int = 5) -> Union[str | List[Content]]:
        # 判断有没有最后一步的prompt
        contains_available_storylines = "{{available_storylines}}" in prompt

        if round_num == -1:
            start_idx = 0
            end_idx = len(self.scripts)
        else:
            start_idx = round_num * round_size
            end_idx = min(len(self.scripts), (round_num + 1) * round_size)

        scripts = "\n".join([json.dumps(s, ensure_ascii=False, indent=4) for s in self.scripts[start_idx:end_idx]])

        if isinstance(self.stories, Dict):
            stories = "\n".join([json.dumps(s, ensure_ascii=False, indent=4) for s in self.stories[start_idx:end_idx]])
        else:
            stories = self.stories

        storyline_definition_str = json.dumps(self.storyline_definition, ensure_ascii=False, indent=4)
        
        env = Environment(
            undefined=KeepMacroUndefined,  # 让 Jinja2 遇到未定义变量时保持原样
            autoescape=True
        )
        tpl = env.from_string(prompt)
        rendered_prompt = tpl.render(
            scripts=scripts,
            stories=stories,
            relationships=self.relationships,
            merged_relationships=self.merge_relationships,
            available_storylines=self.available_storylines,
            # 增加了固定宏 {{storyline_definition}}
            storyline_definition=storyline_definition_str,
            # 保留视频宏，视频宏需要额外处理
            videos="{{videos}}",
            start_ep=start_idx+1,
            end_ep=end_idx,
            num_ep=end_idx-start_idx
        )

        if contains_available_storylines:
            final_prompt = self._apply_storyline_generation(rendered_prompt)
        else:
            final_prompt = rendered_prompt  # 直接返回渲染结果，不做二次替换

        logging.info(f"Prompt: \n{final_prompt}")

        if "{{videos}}" in final_prompt:
            # Video 需要做特殊处理
            return _transform_to_content(final_prompt, self.videos[start_idx:end_idx])
        else:
            return final_prompt

