"""MiniCode Streamlit Web UI — Chinese-native coding assistant interface."""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env
env_file = _PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v and v != "your-key-here":
                    os.environ[k] = v

import streamlit as st
from src.core.llm import create_llm_from_env
from src.core.loop import AgentLoop
from src.core.tool_use import ToolRegistry
from src.tools import register_all_tools
from src.skills.router import SkillRouter
from src.memory.store import MemoryStore

st.set_page_config(page_title="MiniCode", page_icon="🤖", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""<style>
    .main-header { font-size: 1.3rem; font-weight: 600; }
    .tool-result { background: #F1F5F9; padding: 0.5rem; border-radius: 6px;
        margin: 0.3rem 0; font-size: 0.8rem; border-left: 3px solid #3B82F6; }
    .skill-tag { display: inline-block; background: #EEF2FF; color: #3B82F6;
        padding: 0.15rem 0.5rem; border-radius: 10px; font-size: 0.75rem; margin: 0.1rem; }
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    .code-block { background: #1E1E1E; color: #D4D4D4; padding: 0.5rem;
        border-radius: 6px; font-family: 'Consolas', monospace; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)


@st.cache_resource
def get_agent():
    llm = create_llm_from_env()
    tools = ToolRegistry()
    register_all_tools(tools)
    from src.security.guard import SecurityGuard
    from src.context.compressor import ContextCompressor
    from src.memory.store import MemoryStore
    security = SecurityGuard()
    compressor = ContextCompressor()
    memory = MemoryStore()
    return AgentLoop(
        llm=llm, tools=tools, cwd=str(Path.cwd()),
        security_guard=security, compressor=compressor, memory_store=memory,
    )


def main():
    st.markdown('<div class="main-header">🤖 MiniCode — 本地 AI 编程助手</div>', unsafe_allow_html=True)

    agent = get_agent()
    skill_router = SkillRouter()
    memory = MemoryStore()

    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 系统状态")
        stats = memory.get_stats()
        col1, col2 = st.columns(2)
        col1.metric("记忆片段", stats["episodes"])
        col2.metric("经验模式", stats["patterns"])

        st.divider()
        st.markdown("### 🛠 可用工具")
        for t in agent.tools.list():
            st.caption(f"**{t.name}** — {t.description[:50]}")

        st.divider()
        st.markdown("### 🎯 可用技能")
        for s in skill_router._skills.values():
            with st.expander(f"{s.name} — {s.description}"):
                st.caption(s.instructions)
                if s.examples:
                    st.caption("示例: " + ", ".join(s.examples))
                st.caption(f"关键词: {', '.join(s.keywords[:5])}")

        st.divider()
        st.markdown("### 🧠 记忆查看")
        if st.button("查看最近记忆"):
            episodes = memory.search_episodes("", limit=10)
            if episodes:
                for ep in episodes[:5]:
                    with st.expander(f"{ep['task'][:40]}... ({ep['outcome'][:30]}...)"):
                        st.caption(f"任务: {ep['task']}")
                        st.caption(f"结果: {ep['outcome']}")
                        if ep.get('tool_calls'):
                            st.caption(f"工具: {', '.join(ep['tool_calls'])}")
                        st.caption(f"标签: {ep.get('tags', '无')}")
            else:
                st.caption("暂无记忆")

        st.divider()
        st.markdown("### 🎯 匹配技能")
        if "last_skills" in st.session_state and st.session_state.last_skills:
            for s in st.session_state.last_skills:
                st.markdown(f'<span class="skill-tag">{s.name}</span>', unsafe_allow_html=True)
        else:
            st.caption("发起任务后自动匹配")

    # Chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tools"):
                for tr in msg["tools"]:
                    status = "✓" if tr["success"] else "✗"
                    st.markdown(
                        f'<div class="tool-result">'
                        f'<b>{status} {tr["name"]}</b> ({tr.get("duration", 0)}ms)<br>'
                        f'<span style="color:#666">{str(tr.get("output",""))[:300]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            if msg.get("skills"):
                st.caption("匹配技能: " + ", ".join(msg["skills"]))

    # Input
    if prompt := st.chat_input("输入编程任务，例如：「修复 auth 模块的导入错误」"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Skill routing
        skills = skill_router.route(prompt)
        skill_names = [s.name for s in skills]
        st.session_state.last_skills = skills

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                # Inject skills
                instructions = skill_router.get_instructions(skill_names)
                agent.inject_skills(instructions)

                # Inject memory
                episodes = memory.search_episodes(prompt, limit=3)
                patterns = memory.find_patterns(prompt, limit=3)
                agent.inject_memory(episodes, patterns)

                # RAG search
                enhanced_prompt = prompt
                try:
                    from src.rag_link import RAGConnector
                    rag = RAGConnector()
                    ctx = rag.get_context_for_task(prompt)
                    if ctx:
                        enhanced_prompt = prompt + "\n\n[知识库参考]\n" + ctx[:1000]
                except Exception:
                    pass

                result = agent.run(enhanced_prompt)

            st.markdown(result.content)

            tool_info = []
            for tr in result.tool_results:
                tool_info.append({
                    "name": tr.tool_name,
                    "success": tr.success,
                    "output": tr.output[:500],
                    "duration": f"{tr.duration_ms:.0f}",
                })
                status = "✓" if tr.success else "✗"
                st.markdown(
                    f'<div class="tool-result">'
                    f'<b>{status} {tr.tool_name}</b> ({tr.duration_ms:.0f}ms)<br>'
                    f'<span style="color:#666">{tr.output[:300]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Record to memory
            memory.record_episode(
                task=prompt,
                tool_calls=[tr.tool_name for tr in result.tool_results],
                outcome=result.content[:200],
                error="",
                tags=",".join(skill_names),
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": result.content,
                "tools": tool_info,
                "skills": skill_names,
            })


if __name__ == "__main__":
    main()
