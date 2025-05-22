import logging

from fastapi import FastAPI
from game_script import create_script_interface
from plot_understanding import create_plot_interface
import gradio as gr
import uvicorn

from storyline_extractor import create_storyline_extractor_interface

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI TOOL SPACE")
tools = gr.TabbedInterface(
    [create_storyline_extractor_interface(), create_script_interface(), create_plot_interface()],
    ["短剧高光故事线提取", "脚本合成", "剧情理解"],
    title="AI 工具广场")
app = gr.mount_gradio_app(app, tools, path="/gradio")


if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=9210)
    # tools.launch(server_name="0.0.0.0", server_port=7860, share=True)
    uvicorn.run(app=app, host="0.0.0.0", port=9210)
