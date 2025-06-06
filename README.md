# 功能介绍
Pilotscript 是基于 Google VertexAI 平台开发的影视高光故事线生成工具。它整合 Sonix 视频解析与 Gemini 内容生成技术，通过 Gradio 构建交互界面，利用 Jinja 渲染提示词，实现从视频分析到故事线生成的全流程贯通。​
工具采用分步生成模式，支持人工干预修改，兼具智能性与灵活性，能快速提炼影视高光片段，大幅提升视频剪辑师筛选素材的效率，为影视后期制作提供高效智能方案。

![image](https://github.com/user-attachments/assets/d23a06d3-2e9b-4a67-9864-710f2facec08)
# 使用方法
首先，需要在项目的根目录添加vertexAI账号的配置.json文件，里面包含账户与API key，示例：<u>**solar-router-xxxxxx.json**</u>内包含
```
{
  "type": "service_account",
  "project_id": "solar-router-xxxxxx",
  "private_key_id": "",
  "private_key": "",
  "client_email": "",
  "client_id": "",
  "auth_uri": "",
  "token_uri": "",
  "auth_provider_x509_cert_url": "",
  "client_x509_cert_url": "",
  "universe_domain": ""
}
```

配置完成后安装依赖(推荐使用隔离的conda环境）：
```
pip install -r requirements.txt
```

在项目文件的根目录运行，即可成功启动服务。
```
python app.py
```

在浏览器中输入产生的本地地址后（常规为）即可访问到交互页面。使用时，从本地上传文件，或给出google cloud storage链接。prompts中支持的宏列表，用户可以在调用模型时自由应用。
![image](https://github.com/user-attachments/assets/0aa237f6-c913-4c96-b8b5-971bdb1254d5)

调用sonix模型，可以一键生成影视剧的字幕提取。
![image](https://github.com/user-attachments/assets/5dcaa8f2-08ad-4e17-bdf9-75813224dd3f)

短剧故事线生成时，支持自由设置gemini模型的版本及参数。交互界面内置有prompt供用户参考。
![image](https://github.com/user-attachments/assets/231cf5d4-b711-4d03-93d5-b43f122f68be)

产生结果后，界面将反馈本次模型调用的输入输出token数，帮用户更好的了解资源使用情况。
![image](https://github.com/user-attachments/assets/d3670127-13e7-4f0f-92ec-33e9c34fd577)

按照步骤依次运行，该工具能够生成多段逻辑完整的高光故事线供用户参考。示例：
```
```json
[
{
"highlight": "{{遗产争夺}}",
"episodes": "1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 41, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 57, 58",
"main_characters": ["Emma Vanderbilt", "Ethan Vanderbilt", "Daniel", "Evelyn Vanderbilt", "Liam"],
"storyline": "Rodney Vanderbilt去世后，留下巨额遗产，包括Vanderbilt集团的股份和个人财产。Emma作为Rodney的女儿，成为了遗产的第一继承人。然而，Rodney的死因成谜，他的遗产也成为了家族内部以及外部势力争夺的目标。Ethan作为Rodney的弟弟，一直觊觎Vanderbilt集团的控制权，他试图以双倍价格收购Emma手中的股份，并在股东大会上公开质疑Emma的能力，意图夺取公司控制权。Daniel作为Emma的未婚夫，表面上关心Emma，实则与Evelyn有染，两人合谋修改遗嘱，企图侵吞Emma的遗产。Liam最初以保镖的身份接近Emma，暗中调查Rodney的死因，并在遗产争夺中扮演了关键角色。Evelyn作为Emma的继母，也参与了遗产的争夺，她与Daniel合谋，试图从Emma手中分一杯羹。随着剧情发展，Liam逐渐揭露了Daniel和Evelyn的阴谋，并帮助Emma保住了自己的继承权。最终，Emma在Liam的帮助下，成功挫败了Ethan、Daniel和Evelyn的阴谋，继承了父亲的遗产，并继续掌管Vanderbilt集团。在经历了种种波折后，Emma和Liam走到了一起，开始了新的生活。",
"reason": "该情节清晰展现了家族成员以及相关人士为争夺遗产的冲突，多个角色围绕Rodney的遗产展开明争暗斗，包括公司股份、个人财产和保险金，完全符合“遗产争夺”的定义。第一集中，Ethan 就对 Emma 表现出明显的敌意，并试图收购她的股份，显示出他对遗产的觊觎。后续几集中，Daniel 和 Evelyn 的阴谋逐渐显露，他们修改遗嘱、替换 Emma 的药物，都旨在夺取 Emma 的遗产。Liam 的出现则为 Emma 提供了帮助，他不仅保护 Emma 的安全，还帮助她调查父亲的死因和遗产的去向。最终，Emma 成功地保住了自己的遗产，并与 Liam 走到了一起。整个故事线围绕着遗产争夺展开，各方势力的角逐和冲突贯穿始终，体现了“遗产争夺”这一主题。",
"clips": [
    {
        "No.": 1,
        "episodes": "1, 2, 3, 4",
        "storyline": "Rodney Vanderbilt 突然去世，留下巨额遗产和 Vanderbilt 集团的股份。他的弟弟 Ethan 对 Emma 继承的股份虎视眈眈，试图以双倍价格收购，并在股东大会上质疑 Emma 的管理能力。与此同时，Emma 被注射不明液体和绑架，暗示她身处危险之中。Liam 作为 Emma 的新保镖出现，成功解救了她。Ethan 的夺权行为和 Emma 的危险处境，都预示着围绕遗产的争夺战即将展开。Liam 的出现为 Emma 提供了保护，也为后续的遗产争夺埋下了伏笔。"
    },
    {
        "No.": 2,
        "episodes": "26, 27, 28, 29, 30",
        "storyline": "律师 Joe 宣读了 Rodney 的遗嘱，Emma 继承了大部分股份，Daniel 则需要在结婚一年后才能获得剩余的 10% 股份。Ethan 和 Daniel 对此结果表示不满，Ethan 联合其他董事质疑 Emma 的能力，并试图收购 Emma 的股份。Daniel 也劝说 Emma 接受收购提议。Emma 拒绝了他们的要求，并宣布自己已经恢复视力。Ethan 恼羞成怒，试图对 Emma 动手，但被 Liam 阻止。在随后的个人财产遗嘱宣读中，Evelyn 和 Daniel 对遗产分配表示怀疑，认为 Rodney 的财产不止这些，并怀疑遗嘱的真实性。这场遗产争夺战达到了高潮，Emma 坚决捍卫自己的继承权，与 Ethan 和 Daniel 展开了正面交锋。"
    },
    {
        "No.": 3,
        "episodes": "35, 36, 37, 38, 39",
        "storyline": "Daniel 和 Evelyn 计划通过投资洗钱，Liam 将此事告知 G，并对 Daniel 的意图产生怀疑。Emma 发现 Daniel 和 Evelyn 的婚外情，并意识到 Daniel接近她的目的就是为了遗产。Daniel 向 Emma 坦白，并提议与 Emma 合作，帮助 Emma 获得更多遗产，但 Emma 拒绝了。Daniel 离开后，Emma 和 Liam 讨论了 Daniel 的行为，Liam 告诉 Emma 他怀疑 Rodney 的死与 Daniel 有关，并表示会在 Daniel 家寻找线索。Daniel 质问 Emma 并威胁她，Emma 决定报警。这段剧情揭示了 Daniel 的真实面目，他为了遗产不惜欺骗和利用 Emma，加剧了遗产争夺的冲突。Liam 的调查和 Emma 的怀疑，也为后续剧情的发展埋下了伏笔。"
    },
    {
        "No.": 4,
        "episodes": "46, 47, 48, 49, 50",
        "storyline": "Daniel 和 Evelyn 面临高利贷的追债，走投无路之下，Daniel 决定向 Emma 忏悔并寻求帮助。Emma 却指责 Daniel 杀害了她的父亲。Daniel 否认，并试图恐吓 Emma，最终恼羞成怒，掐住 Emma 的脖子。Liam 出现并救下 Emma。Evelyn 来到 Emma 的房间，感谢 Emma 对 Rodney 的照顾，并留下了一张卡作为 Emma 的生活费。Emma 表示会将 Daniel 绳之以法。Daniel 试图挑拨 Emma 和 Liam 的关系，但 Emma 表示相信 Liam。这段剧情展现了 Daniel 的疯狂和 Evelyn 的无奈，也突出了 Emma 和 Liam 之间的信任和感情。遗产争夺的冲突进一步升级，Daniel 的罪行即将暴露。"
    }]
```
也可以使用data_processing文件夹中的脚本生成更加直观的excel格式表。
![image](https://github.com/user-attachments/assets/d828a41e-0fd0-4834-b1bd-d148f17e42b5)




