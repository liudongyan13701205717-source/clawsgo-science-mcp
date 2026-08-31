"""MCP stdio server 入口：注册三条功能线的工具集。

阶段 0：仅注册工具签名（空实现 stub），打通 opencode MCP 通道；
后续阶段在各自模块内填充真实实现。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from clawsgo_self import __version__

mcp = FastMCP(
    "clawsgo-self",
    instructions=(
        "ClawsGO Science 复刻：论文复现五步闭环、论文写作助力、端到端交付。"
        "所有工具均本地自建，不依赖 ClawsGO 官方站点。"
    ),
)


@mcp.tool()
def reproduce_paper(
    pdf_path: str,
    framework: str = "pytorch",
) -> dict:
    """论文复现五步闭环：解析 PDF → 复现方案 → 生成代码 → 沙箱运行比对 → 产出交付物。

    Args:
        pdf_path: 论文 PDF 的本地绝对路径。
        framework: 生成代码框架，`pytorch` 或 `tensorflow`，默认 pytorch。
    """
    from clawsgo_self.reproduce.api import reproduce_paper as _impl

    return _impl(pdf_path=pdf_path, framework=framework)


@mcp.tool()
def reproduce_status(task_id: str) -> dict:
    """查询论文复现任务的异步状态与阶段进度。"""
    from clawsgo_self.reproduce.api import reproduce_status as _impl

    return _impl(task_id=task_id)


@mcp.tool()
def write_section(
    paper_id: str,
    section: str,
    prompt: str,
    format: str = "latex",
) -> dict:
    """论文写作助力：按章节引导生成内容（摘要/问题/假设/符号/建模/求解/结果/参考文献/附录）。

    Args:
        paper_id: 论文/项目标识。
        section: 章节名，如 abstract/introduction/problem/assumptions/notation/
            modeling/solution/results/references/appendix。
        prompt: 该章节的写作引导/要点。
        format: 输出格式，`latex` 或 `markdown`。
    """
    from clawsgo_self.write.api import write_section as _impl

    return _impl(paper_id=paper_id, section=section, prompt=prompt, format=format)


@mcp.tool()
def export_document(
    paper_id: str,
    target: str = "pdf",
) -> dict:
    """论文写作助力：将已写 doc（markdown）导出为 LaTeX / PDF / docx。

    Args:
        paper_id: 论文/项目标识。
        target: 导出目标，`pdf` 或 `docx`（LaTeX 源始终生成）。
    """
    from clawsgo_self.export.api import export_document as _impl

    return _impl(paper_id=paper_id, target=target)


@mcp.tool()
def get_deliverables(task_id: str = "") -> dict:
    """端到端交付：列出某任务（复现/写作）的交付物清单（图/数据/源码/报告）。

    Args:
        task_id: 复现任务 ID（或写作项目 ID，二者其一）。
    """
    from clawsgo_self.deliver.api import get_deliverables as _impl

    return _impl(task_id=task_id)


@mcp.tool()
def ideate_paper(
    topic: str,
    paper_id: str,
) -> dict:
    """研究起点：由研究方向构思选题，产出研究缺口、候选假设、多视角评审与实验计划。

    Args:
        topic: 研究方向/主题/关键词。
        paper_id: 论文/项目标识（产物存 projects/{paper_id}/research/）。
    """
    from clawsgo_self.core import get_layout
    from clawsgo_self.research.api import ideate_paper as _impl

    return _impl(topic=topic, paper_id=paper_id, layout=get_layout())


@mcp.tool()
def inject_results(
    paper_id: str,
    task_id: str,
    section: str = "results",
) -> dict:
    """将复现任务的真实实验结果并入论文对应章节（实验数据→论文）。

    Args:
        paper_id: 论文/项目标识。
        task_id: 已完成复现闭环的任务 ID。
        section: 注入目标章节，`results` 或 `experiments`。
    """
    from clawsgo_self.core import get_layout
    from clawsgo_self.research.api import inject_results as _impl

    return _impl(paper_id=paper_id, task_id=task_id, layout=get_layout(), section=section)


@mcp.tool()
def research_verdict(task_id: str) -> dict:
    """结果分析自旋门：根据复现产物给出 PROCEED/REFINE/PIVOT 决策建议。

    Args:
        task_id: 已完成复现闭环的任务 ID。
    """
    from clawsgo_self.core import get_layout
    from clawsgo_self.research.api import decision_readout as _impl

    return _impl(task_id=task_id, layout=get_layout())


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
