"""研究计划书（research_plan）：由选题展开成完整研究计划。

产出：RQ/假设/目标/贡献/方法/数据/基线/指标/消融/里程碑/风险/计算资源。
落盘 projects/{paper_id}/research/research_plan.{json,md}。
无 LLM 时基于关键词 + 预设模板做确定性展开；可 LLM 增强细化。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from clawsgo_self.core import Layout
from clawsgo_self.core import model as llm

_FIELDS = ["rq", "hypotheses", "objectives", "contributions", "methods",
           "datasets", "baselines", "metrics", "ablation", "milestones",
           "risks", "compute"]

_LABELS = {
    "rq": "研究问题", "hypotheses": "核心假设", "objectives": "研究目标",
    "contributions": "主要贡献", "methods": "方法/模型", "datasets": "数据与基准",
    "baselines": "基线方法", "metrics": "评估指标", "ablation": "消融设计",
    "milestones": "里程碑", "risks": "风险与规避", "compute": "计算与资源",
}


@dataclass
class ResearchPlan:
    ok: bool
    paper_id: str = ""
    topic: str = ""
    rq: str = ""
    hypotheses: list = field(default_factory=list)
    objectives: list = field(default_factory=list)
    contributions: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    datasets: list = field(default_factory=list)
    baselines: list = field(default_factory=list)
    metrics: list = field(default_factory=list)
    ablation: list = field(default_factory=list)
    milestones: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    compute: str = ""
    notes: list = field(default_factory=list)
    error: str = ""
    llm_used: bool = False

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("ok", "paper_id", "topic") + tuple(_FIELDS) + ("notes", "error", "llm_used")}

    def to_markdown(self) -> str:
        def bullet(xs):
            return "\n".join(f"- {x}" for x in xs) if xs else "- （待细化）"

        lines = [f"# 研究计划书（{self.paper_id}）", f"**主题：** {self.topic}", ""]
        for k in _FIELDS:
            v = getattr(self, k)
            label = _LABELS.get(k, k)
            if isinstance(v, list):
                lines += [f"## {label}", bullet(v), ""]
            else:
                lines += [f"## {label}", v or "（待细化）", ""]
        return "\n".join(lines)


def _empty() -> ResearchPlan:
    return ResearchPlan(ok=False)


def research_plan(*, topic: str, paper_id: str, layout: Layout) -> ResearchPlan:
    topic = (topic or "").strip()
    if len(topic) < 4:
        r = _empty()
        r.paper_id, r.error = paper_id, "研究主题过短或不合法。"
        return r

    r = _template(topic, paper_id)
    if llm.configured():
        try:
            _llm_enhance(r)
            r.llm_used = True
        except RuntimeError as e:
            r.notes.append(f"LLM 增强不可用，保留模板计划：{e}")

    r.ok = True
    _persist(layout, paper_id, r)
    return r


def _template(topic: str, paper_id: str) -> ResearchPlan:
    toks = [t for t in re.split(r"[\s，。、,;；：:/]+|和|与|的|基于|面向", topic) if t]
    top = toks[:2] or [topic]
    base = "、".join(top)
    return ResearchPlan(
        ok=False, paper_id=paper_id, topic=topic,
        rq=f"我们如何针对「{base}」设计并验证一种有效方法，使其在指标上显著优于现有基线？",
        hypotheses=[f"H1：面向 {base} 的定制化建模/约束能带来稳定的性能增益。",
                     f"H2：{base} 的收益在不同规模/数据分布下可迁移（鲁棒性）。"],
        objectives=[f"O1：形式化 {base} 的研究问题与评估协议。",
                     f"O2：实现并验证针对 {base} 的 {len(top)} 个候选方法。",
                     "O3：给出消融与可解释性分析，定位增益来源。"],
        contributions=[f"C1：提出面向 {base} 的 新方法/框架。",
                        "C2：构建公开基准与可复现实验管线。",
                        "C3：输出经验结论与设计准则。"],
        methods=[f"M1：{base} 的基线方案（最简实现）。",
                 f"M2：基于 {base} 的增强方案（本文核心）。"],
        datasets=["公开数据集/基准（待选定，至少 2 个）", "消融用自定义子集"],
        baselines=["最先进基线（SOTA）", "经典方法", "消融变体"],
        metrics=["主指标（accuracy / loss / 延迟等）", "次指标（鲁棒性、参数量、能耗）"],
        ablation=["逐组件消融", "超参数敏感性", "规模/分布泛化测试"],
        milestones=["W1：文献与数据集确定", "W2：基线实现与流水线", "W3：核心方法+消融", "W4：写作与复现验证"],
        risks=["R1：数据/算力受限 → 缩减规模或选用小基准", "R2：增益不显著 → 加强针对性设计/换角度评估"],
        compute="单机 GPU（建议 ≥8GB），预算有限时优先小模型与小基准",
    )


def _llm_enhance(r: ResearchPlan) -> None:
    sys = "你是科研项目规划助手。基于已有计划，用中文给出更具体、可执行的细化。输出严格 JSON。"
    prompt = ("主题：" + r.topic +
              "\n现计划：" + r.to_markdown() +
              "\n输出 JSON：{\"rq\":\"\",\"hypotheses\":[\"\"],\"objectives\":[\"\"],"
              "\"contributions\":[\"\"],\"methods\":[\"\"],\"datasets\":[\"\"],"
              "\"baselines\":[\"\"],\"metrics\":[\"\"],\"ablation\":[\"\"],"
              "\"milestones\":[\"\"],\"risks\":[\"\"],\"compute\":\"\"}")
    raw = llm.chat(prompt, system=sys, temperature=0.5, max_tokens=1600)
    d = _strip_json_obj(raw)
    if not d:
        return
    if isinstance(d.get("rq"), str) and d["rq"].strip():
        r.rq = d["rq"].strip()
    for k in ("hypotheses", "objectives", "contributions", "methods",
              "datasets", "baselines", "metrics", "ablation", "milestones", "risks"):
        v = d.get(k)
        if isinstance(v, list) and v:
            setattr(r, k, [str(x) for x in v][:8])
    if isinstance(d.get("compute"), str) and d["compute"].strip():
        r.compute = d["compute"].strip()


def _strip_json_obj(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j < i:
        return {}
    try:
        d = json.loads(s[i : j + 1])
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        return {}


def _persist(layout: Layout, paper_id: str, r: ResearchPlan) -> Path:
    root = layout.project_dir(paper_id) / "research"
    root.mkdir(parents=True, exist_ok=True)
    p = root / "research_plan.json"
    p.write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md = root / "research_plan.md"
    md.write_text(r.to_markdown(), encoding="utf-8")
    return p
