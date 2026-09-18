#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""confirm —— 逐步骤确认台账。

用户的硬要求：**每一个步骤都要让用户确认一下。**
所以每一次「确认」都要留下记录，而不是靠 Agent 自己记得问过。

为什么要台账而不是靠对话：
  * 一条 MV 有十几个决策点（材料、音乐、歌词、Canon、三视图、画风、分段、
    **每一条提示词**、**每一段尾帧**、渲染、校验、打包）；
  * 中途可能换会话、换人、隔天继续；
  * 用户说「我没同意过这个画风」时，台账是唯一能查的东西。

所以 `render` 与 `pack` 会**拒绝**在缺确认的情况下继续，除非显式 `--unattended`
（无人值守模式，明确表示「我已经全部确认过了」）。
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

LEDGER_NAME = "confirmations.json"

# 每个步骤的标题与「用户到底在确认什么」
STEP_LABELS = {
    "gate": (u"材料与时长闸门", u"材料齐不齐、歌是不是 ≤3 分钟"),
    "analyze": (u"音乐实测", u"BPM / 拍网格 / 段落能量对不对（错了后面卡点全错）"),
    "lyrics": (u"歌词时间轴", u"歌词与时间轴（ASR 的一定要人工核对）"),
    "canon": (u"人物 Canon", u"脸/发型/服装/配饰/轮廓填得对不对"),
    "threeview": (u"三视图", u"转面表出图了、像同一个人"),
    "styles": (u"画风路线", u"这一条 MV 用哪条融合路线"),
    "segments": (u"分段与切点", u"14.5 秒的切点落在哪里、每段画风"),
    "ending": (u"收尾效果", u"全片最后一下是什么（不一定是站定）"),
    "render": (u"H3 提示词", u"提示词包可以交付了"),
    "validate": (u"校验结果", u"校验里的问题都处理了"),
    "pack": (u"交付包", u"上传操作单可以照着执行了"),
}


def label_for(step):
    if step in STEP_LABELS:
        return STEP_LABELS[step]
    if step.startswith("prompt-"):
        return (u"第 %s 条提示词" % step.split("-", 1)[1],
                u"这一条的歌词绑定、背景元素、运镜、延续上一帧")
    if step.startswith("chain-"):
        return (u"第 %s 段尾帧" % step.split("-", 1)[1],
                u"尾帧截对了（不是首帧）、动作接得上")
    return (step, u"—")


class Ledger(object):
    def __init__(self, project_root=None, path=None):
        self.path = path or os.path.join(
            project_root or common.PROJECT_ROOT, "workspace", LEDGER_NAME)
        self._data = common.read_json(self.path, None) or {"steps": {}}
        self._data.setdefault("steps", {})

    # ------------------------------------------------------------ 读写
    def confirm(self, step, note=None, by=None):
        self._data["steps"][step] = {
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "by": by or "user",
            "note": note or "",
        }
        self.save()
        return self._data["steps"][step]

    def confirm_all(self, steps, note=None, by=None):
        for s in steps:
            self._data["steps"][s] = {
                "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "by": by or "user",
                "note": note or u"批量确认",
            }
        self.save()
        return len(steps)

    def revoke(self, step):
        if step in self._data["steps"]:
            del self._data["steps"][step]
            self.save()
            return True
        return False

    def save(self):
        common.write_json(self.path, self._data)

    def get(self, step):
        return self._data["steps"].get(step)

    def is_confirmed(self, step):
        return step in self._data["steps"]

    def confirmed(self):
        return sorted(self._data["steps"].keys())

    # ------------------------------------------------------------ 必确认集
    def required_for_render(self, plan):
        """渲染之前必须确认的步骤（含**每一条提示词**与**每一段尾帧**）。"""
        steps = ["gate", "analyze", "lyrics", "canon", "threeview", "styles",
                 "segments", "ending"]
        segs = (plan or {}).get("segments") or []
        for i, seg in enumerate(segs, 1):
            steps.append("prompt-%02d" % i)
            # 每一段的输出都要确认：这一段对不对、尾帧截得对不对。
            # 最后一段没有后继，所以它的确认就是「末段输出确认」。
            steps.append("chain-%02d" % i)
        return steps

    def required_for_pack(self, plan):
        return self.required_for_render(plan) + ["render", "validate"]

    def pending(self, steps):
        return [s for s in steps if not self.is_confirmed(s)]

    def pending_for_render(self, plan):
        return self.pending(self.required_for_render(plan))

    def pending_for_pack(self, plan):
        return self.pending(self.required_for_pack(plan))

    # ------------------------------------------------------------ 展示
    def status(self, plan=None):
        plan = plan or {}
        req = self.required_for_render(plan)
        return {
            "ledger": self.path,
            "confirmed": self.confirmed(),
            "required_for_render": req,
            "pending_for_render": self.pending(req),
            "pending_for_pack": self.pending(self.required_for_pack(plan)),
        }

    def render_md(self, plan=None):
        st = self.status(plan or {})
        lines = [u"# 逐步骤确认台账", ""]
        lines.append(u"> 每一个步骤都要用户确认一次。"
                     u"未确认的步骤，`render` 与 `pack` 会**拒绝**继续。")
        lines.append("")
        lines.append(u"| 步骤 | 是什么 | 状态 | 时间 / 备注 |")
        lines.append(u"|------|--------|------|-------------|")
        for step in st["required_for_render"]:
            title, what = label_for(step)
            rec = self.get(step)
            if rec:
                cell = u"✅ %s" % rec.get("at", "")
                if rec.get("note"):
                    cell += u"　%s" % rec["note"]
            else:
                cell = u"⬜ 待确认"
            lines.append(u"| `%s` | %s | %s | %s |" % (step, title, cell, what))
        lines.append("")
        lines.append(u"## 怎么确认")
        lines.append("")
        lines.append(u"```bash")
        lines.append(u"python3 scripts/mvstudio.py confirm --step gate")
        lines.append(u"python3 scripts/mvstudio.py confirm --step prompt-01 --note \"卡点没问题\"")
        lines.append(u"python3 scripts/mvstudio.py confirm --all     # 一次确认全部")
        lines.append(u"python3 scripts/mvstudio.py confirm --status")
        lines.append(u"```")
        lines.append("")
        if st["pending_for_render"]:
            lines.append(u"**还有 %d 步未确认**：%s"
                         % (len(st["pending_for_render"]),
                            u"、".join(st["pending_for_render"])))
        else:
            lines.append(u"✅ 全部已确认，可以渲染。")
        lines.append("")
        return "\n".join(lines) + "\n"


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="逐步骤确认台账")
    common.add_common_args(ap)
    ap.add_argument("--step", default=None)
    ap.add_argument("--note", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--revoke", default=None)
    ap.add_argument("--plan", default=None)
    args = ap.parse_args(argv)
    common.apply_common_args(args)

    plan_path = args.plan or os.path.join(common.path("workspace_analysis"),
                                          "director_plan.json")
    plan = common.read_json(plan_path, {}) or {}
    led = Ledger()

    if args.revoke:
        ok = led.revoke(args.revoke)
        common.echo(u"已撤销 %s" % args.revoke if ok else u"%s 本来就没确认过" % args.revoke)
        return 0 if ok else 1

    if args.all:
        n = led.confirm_all(led.required_for_render(plan), note=args.note)
        common.echo(u"已一次性确认 %d 个步骤" % n)
        return 0

    if args.step:
        rec = led.confirm(args.step, note=args.note)
        title, what = label_for(args.step)
        common.echo(u"✅ 已确认「%s」：%s%s"
                    % (title, what, (u"　备注：%s" % args.note) if args.note else u""))
        pend = led.pending_for_render(plan)
        if pend:
            nxt = pend[0]
            t2, _ = label_for(nxt)
            common.echo(u"下一步待确认：`%s`（%s）" % (nxt, t2))
            common.echo(u"  python3 scripts/mvstudio.py confirm --step %s" % nxt)
        else:
            common.echo(u"全部步骤已确认，可以跑 render。")
        return 0

    md = led.render_md(plan)
    common.write_text(os.path.join(common.path("output_latest"), "confirmations.md"), md)
    if args.json:
        common.emit(led.status(plan), True)
    else:
        common.echo(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
