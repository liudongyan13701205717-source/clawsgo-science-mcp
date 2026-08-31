"""研究线（构思→辩论→实验设计→注入论文）单元/集成测试。

全程不依赖 LLM（走模板回退）与真实网络（papers 注入 mock）。
"""

from __future__ import annotations

import json

import pytest

from clawsgo_self.core import Layout, get_layout
from clawsgo_self.write.doc import DocStore

_MOCK_PAPERS = [
    {"title": "Interpretability of Large Models", "year": 2023,
     "authors": ["A"], "cited_by": 120, "doi": "10.1/abc"},
    {"title": "Efficient Inference on Edge Devices", "year": 2022,
     "authors": ["B"], "cited_by": 80},
    {"title": "Resource-constrained Learning", "year": 2021,
     "authors": ["C"], "cited_by": 40},
]


def _layout(tmp_path) -> Layout:
    import os

    os.chdir(tmp_path)
    return get_layout()


def test_ideate_produces_gaps_rq_candidates(tmp_path):
    from clawsgo_self.research.ideate import ideate

    r = ideate(
        "大语言模型的轻量化可解释方法",
        layout=_layout(tmp_path),
        paper_id="p_idea",
        papers=_MOCK_PAPERS,
    )
    assert r.ok is True
    assert r.llm_used is False  # 无 LLM → 模板回退
    assert r.gaps and r.questions and r.candidates


def test_ideate_rejects_empty_topic(tmp_path):
    from clawsgo_self.research.ideate import ideate

    r = ideate("   ", layout=_layout(tmp_path), paper_id="p_bad", papers=[])
    assert r.ok is False
    assert "不能为空" in r.error or "过短" in r.error


def test_debate_ranks_and_recommends(tmp_path):
    from clawsgo_self.research import ideate
    from clawsgo_self.research.hypoth import debate

    ir = ideate.ideate(
        "分布式训练", layout=_layout(tmp_path), paper_id="p_d", papers=_MOCK_PAPERS
    )
    dr = debate(ir.candidates, layout=_layout(tmp_path), paper_id="p_d")
    assert dr.ok is True
    assert dr.reviews
    assert dr.reviews[0].rank == 1
    assert dr.recommendation and "推荐" in dr.recommendation


def test_design_produces_plan_markdown(tmp_path):
    from clawsgo_self.research import ideate
    from clawsgo_self.research.design import design

    ir = ideate.ideate(
        "图神经网络泛化", layout=_layout(tmp_path), paper_id="p_m", papers=_MOCK_PAPERS
    )
    cand = ir.candidates[0] if ir.candidates else None
    er = design(cand, layout=_layout(tmp_path), paper_id="p_m")
    assert er.ok is True
    assert er.metrics
    md = er.to_markdown()
    assert "实验设计" in md and "数据集" in md


def test_inject_writes_real_metrics_to_section(tmp_path):
    from clawsgo_self.core import Layout
    from clawsgo_self.research.inject import inject_results

    layout = _layout(tmp_path)
    tid = "task_x"
    task_root = layout.task_dir(tid)
    task_root.joinpath("results.json").write_text(
        json.dumps(
            {
                "ok": True,
                "paper_title": "Demo",
                "metrics": [
                    {"tag": "acc", "value": 0.912, "ptype": "real", "conf": True},
                    {"tag": "loss", "value": 0.21, "ptype": "real", "conf": True},
                ],
                "plots": ["curve.png"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    task_root.joinpath("plan.json").write_text(
        json.dumps({"inferred_hyperparams": {"lr": 0.01}}), encoding="utf-8"
    )
    task_root.joinpath("curve.png").write_bytes(b"PNG")

    out = inject_results(layout=layout, paper_id="paperB", task_id=tid, section="results")
    assert out["ok"] is True
    assert out["metrics_count"] == 2

    store = DocStore(layout, "paperB")
    sec = store.read_section("results") or ""
    assert "0.9120" in sec
    assert "0.2100" in sec


def test_inject_missing_result_raises(tmp_path):
    from clawsgo_self.research.inject import InjectError, inject_results

    layout = _layout(tmp_path)
    with pytest.raises(InjectError):
        inject_results(layout=layout, paper_id="paperC", task_id="ghost_task")


def test_verdict_proceed_when_metrics_and_plot(tmp_path):
    from clawsgo_self.research.api import decision_readout

    layout = _layout(tmp_path)
    tid = "tv"
    task_root = layout.task_dir(tid)
    task_root.joinpath("results.json").write_text(
        json.dumps(
            {
                "ok": True,
                "metrics": [
                    {"tag": "m", "value": 1.0, "ptype": "real", "conf": True},
                    {"tag": "m2", "value": 2.0, "ptype": "real", "conf": True},
                ],
                "plots": ["a.png"],
            }
        ),
        encoding="utf-8",
    )
    v = decision_readout(task_id=tid, layout=layout)
    assert v["verdict"] == "PROCEED"


def test_verdict_pivot_on_failure(tmp_path):
    from clawsgo_self.research.api import decision_readout

    layout = _layout(tmp_path)
    tid = "tf"
    task_root = layout.task_dir(tid)
    task_root.joinpath("results.json").write_text(
        json.dumps({"ok": False, "error": "自愈重试失败"}), encoding="utf-8"
    )
    v = decision_readout(task_id=tid, layout=layout)
    assert v["verdict"] == "PIVOT"
