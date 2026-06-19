# 🤖 MiniCode — 本地 AI 编程助手

参考 Claude Code 架构设计的轻量级终端 AI Coding Agent。**中文原生、国内模型优先、Web UI + 桌面版**。

## 与 MiniCode-Python 的差异

| | MiniCode-Python 原版 | MiniCode（本仓库） |
|---|---|---|
| 语言 | 英文 prompt/UI | **全中文原生** |
| 模型 | Claude/GPT 优先 | **SiliconFlow/DeepSeek/Qwen 一键切换** |
| 界面 | 仅终端 TUI | **终端 + Streamlit Web + 桌面版** |
| 部署 | pip install -e .[dev] | **setup.bat 一键安装** |
| 记忆 | 文件系统 | **SQLite 3 层记忆 + 自动提炼** |
| Skill | 插件式 | **6 内置 Skill + 2 阶段路由匹配** |
| 知识库 | 无 | **可对接 RAG 知识库** |

## 快速开始

```bash
# 1. 双击 setup.bat（或手动）
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env 填入: SILICONFLOW_API_KEY=你的key

# 3. 启动
python cli/main.py chat              # 终端交互
python cli/main.py headless "任务"   # 单次执行
streamlit run web/app.py             # Web 界面
python desktop_app.py                # 桌面版
```

## 内置工具（11个）

read_file, write_file, edit_file, grep, glob, shell, git_status, git_diff, git_log, git_branch, web_fetch

## 内置技能（6个）

fix_bug, add_feature, refactor, explain_code, write_test, fix_import

## 项目结构

```
minicode/
├── cli/main.py          # 终端入口
├── web/app.py           # Web UI
├── desktop_app.py        # 桌面版
├── setup.bat            # 一键安装
├── src/
│   ├── core/            # LLM适配 + Query Loop + Tool Use
│   ├── tools/           # 11个工具
│   ├── memory/          # SQLite记忆 + 自动提炼
│   ├── skills/          # 6个Skill + 2阶段路由
│   ├── context/         # 分层上下文压缩
│   └── security/        # 安全审查
└── config/default.yaml  # 配置文件
```

## License

MIT
