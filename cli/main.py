"""MiniCode CLI — Chinese-native AI coding agent."""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v and v != "your-key-here":
                    os.environ[k] = v

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.core.llm import create_llm_from_env
from src.core.loop import AgentLoop
from src.core.tool_use import ToolRegistry
from src.tools import register_all_tools

app = typer.Typer(name="minicode", help="MiniCode - 本地 AI 编程助手")
console = Console()


def _print_banner():
    console.print(Panel(
        "[bold cyan]🤖 MiniCode[/bold cyan] — 本地 AI 编程助手\n"
        "[dim]基于 Claude Code 架构 | 中文原生 | 国内模型优先[/dim]",
        border_style="cyan",
    ))


@app.command("chat")
def chat(
    prompt: str = typer.Option(None, "-p", "--prompt", help="直接提问（非交互模式）"),
):
    """启动交互式对话或单次提问。"""
    # Init
    llm = create_llm_from_env()
    if not llm._client.api_key:
        console.print("[red]请先设置 API Key！[/red]")
        console.print("创建 .env 文件并填入: SILICONFLOW_API_KEY=你的key")
        raise typer.Exit(1)

    tools = ToolRegistry()
    register_all_tools(tools)

    # Optional modules
    from src.security.guard import SecurityGuard
    from src.context.compressor import ContextCompressor
    from src.memory.store import MemoryStore
    from src.skills.router import SkillRouter

    security = SecurityGuard()
    compressor = ContextCompressor()
    memory = MemoryStore()
    skill_router = SkillRouter()

    cwd = str(Path.cwd())
    agent = AgentLoop(
        llm=llm, tools=tools, cwd=cwd,
        security_guard=security,
        compressor=compressor,
        memory_store=memory,
    )

    # Try RAG connector
    rag = None
    try:
        from src.rag_link import RAGConnector
        rag = RAGConnector()
    except Exception:
        pass

    # Single prompt mode
    if prompt:
        console.print(f"[dim]⏳ 思考中...[/dim]")
        result = agent.run(prompt)
        console.print(Markdown(result.content))
        console.print(f"[dim]Tokens: {agent.total_tokens}[/dim]")
        return

    # Interactive mode
    _print_banner()
    console.print(f"[dim]工作目录: {cwd}[/dim]")
    console.print(f"[dim]模型: {llm.model}[/dim]")
    console.print(f"[dim]可用工具: {len(tools.list())} 个[/dim]")
    console.print("[dim]输入 /help 查看更多命令，输入 /quit 退出[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]你:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见！[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]再见！[/dim]")
            break
        if user_input == "/help":
            _show_help()
            continue
        if user_input == "/tools":
            _show_tools(tools)
            continue
        if user_input == "/stats":
            console.print(f"[dim]已用 Tokens: {agent.total_tokens}[/dim]")
            continue

        console.print("[dim]⏳ 思考中...[/dim]")
        try:
            # Skill routing
            skills = skill_router.route(user_input)
            if skills:
                instructions = skill_router.get_instructions([s.name for s in skills])
                agent.inject_skills(instructions)
                console.print(f"[dim]匹配技能: {', '.join(s.name for s in skills)}[/dim]")

            # Memory injection
            episodes = memory.search_episodes(user_input, limit=3)
            patterns = memory.find_patterns(user_input, limit=3)
            agent.inject_memory(episodes, patterns)

            # RAG search
            if rag:
                rag_ctx = rag.get_context_for_task(user_input)
                if rag_ctx:
                    user_input += "\n\n[知识库参考]\n" + rag_ctx[:1000]

            result = agent.run(user_input)
            console.print()
            console.print(Markdown(result.content))
            if result.tool_results:
                for tr in result.tool_results:
                    status = "✓" if tr.success else "✗"
                    color = "green" if tr.success else "red"
                    console.print(
                        f"  [{color}]{status} {tr.tool_name}[/{color}] "
                        f"({tr.duration_ms:.0f}ms)"
                    )
            console.print(f"[dim]Tokens: {agent.total_tokens}[/dim]\n")
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


def _show_help():
    table = Table(title="可用命令")
    table.add_column("命令", style="cyan")
    table.add_column("说明")
    table.add_row("/help", "显示此帮助")
    table.add_row("/tools", "列出所有可用工具")
    table.add_row("/stats", "查看 Token 使用量")
    table.add_row("/quit", "退出")
    console.print(table)


def _show_tools(tools: ToolRegistry):
    table = Table(title="可用工具")
    table.add_column("工具", style="cyan")
    table.add_column("分类")
    table.add_column("说明")
    for t in tools.list():
        table.add_row(t.name, t.category, t.description[:60])
    console.print(table)


@app.command("headless")
def headless(
    task: str = typer.Argument(..., help="要执行的任务描述"),
):
    """单次执行模式（非交互）。"""
    llm = create_llm_from_env()
    tools = ToolRegistry()
    register_all_tools(tools)
    agent = AgentLoop(llm=llm, tools=tools, cwd=str(Path.cwd()))
    console.print(f"[dim]执行: {task[:80]}...[/dim]")
    result = agent.run(task)
    console.print(Markdown(result.content))


if __name__ == "__main__":
    app()
