from typing import Any, Dict

import vertexai
from vertexai.generative_models import SafetySetting, GenerativeModel


class VertexaiClient:
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

    def __init__(self, project: str, location: str, api_endpoint: str):
        vertexai.init(
            project=project,
            location=location,
            api_endpoint=api_endpoint
        )

        self._llm_dict = {}

    def _chat(self, model_name, contents, generation_config: Dict[str, Any], stream: bool):
        if self._llm_dict.get(model_name) is None:
            self._llm_dict[model_name] = GenerativeModel(model_name)

        responses = self._llm_dict.get(model_name).generate_content(
            contents,
            generation_config=generation_config,
            safety_settings=self.SAFETY_SETTINGS,
            stream=stream,
        )

        return responses

    def chat(self, model_name, contents, generation_config: Dict[str, Any]):
        return self._chat(model_name, contents, generation_config, False)

    def stream_chat(self, model_name, contents, generation_config: Dict[str, Any]):
        return self._chat(model_name, contents, generation_config, True)
