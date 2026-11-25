from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime" / "src"))
from origin_sciplot.origin_backend import verify_utils as verify


class TextObject:
    def __init__(self, name="Legend", kind=3, show=True, text=r"\b(CO\-(2))"):
        self.name, self.kind, self.show, self.text = name, kind, show, text
        self.props = {"font": 1, "fsize": 17, "bold": 0}

    def GetName(self): return self.name
    def GetObjectType(self): return self.kind
    def GetShow(self): return self.show
    def GetText(self): return self.text
    def get_float(self, key): return self.props[key]
    def set_float(self, key, value): self.props[key] = value


class WindowsTextObject(TextObject):
    @property
    def text(self): return self._text

    @text.setter
    def text(self, value):
        self._text = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


class Plot:
    def __init__(self, owner, index, kind=202):
        self.owner, self.index, self.layer = owner, index, owner
        self.options = dict(pt=kind, s=0, c=123, w=1500, cse=-9, csf=-9, kf=9, k=3,
                            z=15, kh=255, qs=17, qf=1, qb=0)
        self.writes = []

    def lt_range(self): return f"[Graph1]1!{self.index}"
    def set_cmd(self, command):
        flag, value = command.split()
        self.writes.append(flag)
        self.options[flag[1:]] = float(value)
        if self.owner.corrupt_mark:
            self.options[self.owner.corrupt_mark] = 999


class FakeOrigin:
    def __init__(self):
        self.texts = [TextObject(), TextObject("Hidden", kind=2, show=False)]
        self.obj = SimpleNamespace(GraphObjects=self.texts)
        self.plots = [Plot(self, 1), Plot(self, 2, 231)]
        self.variables, self.axis_props = {}, {}
        self.reads, self.fail_flag, self.corrupt_mark = [], None, None
        self.axes = {"x": 1, "y": 3, "z": 0}

    def activate(self): pass
    def plot_list(self): return self.plots
    def label(self, name): return next(t for t in self.texts if t.name == name)
    def set_float(self, key, value): self.axis_props[key] = value
    def get_float(self, key): return self.axis_props[key]
    def lt_float(self, name):
        if name == "font(Arial)":
            return 71
        if name.startswith("layer."):
            return self.axes[name.split(".")[1]]
        return self.variables[name]
    def LT_execute(self, command):
        init = re.fullmatch(r"(\w+)=NANUM;", command)
        if init:
            self.variables[init[1]] = math.nan
            return True
        read = re.search(r"range rr=\[Graph1\]1!(\d+);get rr -(\w+) (\w+);", command)
        if read:
            index, flag, variable = int(read[1]), read[2], read[3]
            self.reads.append((index, flag))
            if flag != self.fail_flag:
                self.variables[variable] = self.plots[index - 1].options[flag]
            return True
        assert command == "doc -uw;"
        return True
    lt_exec = LT_execute


@pytest.fixture
def native(monkeypatch):
    origin = FakeOrigin()
    monkeypatch.setattr(
        verify, "read_page_geometry_cm", lambda *_: {"width_cm": 28.8544, "height_cm": 20.14982}
    )
    return origin


def style(**overrides):
    fields = dict(font_family="Arial", axis_title_size_pt=28, tick_label_size_pt=26,
                  legend_size_pt=24, annotation_size_pt=24, bold=True)
    fields.update(overrides)
    return SimpleNamespace(personal_profile={"id": "test", "overrides": fields})


def test_native_legend_and_visible_axes_change_without_showing_hidden_objects(native):
    report = verify.apply_personal_typography(native, [native], style())
    assert [t["name"] for t in report["texts"]] == ["Legend"]
    assert native.texts[0].props == {"font": 71, "fsize": 24, "bold": 0}
    assert native.texts[0].text == r"\b(CO\-(2))"
    assert report["texts"][0]["bold"] == 1
    assert report["texts"][0]["bold_source"] == "inline_markup"
    assert native.texts[1].props["fsize"] == 17 and native.texts[1].show is False
    assert {a["axis"] for a in report["axes"]} == {"x", "y", "y2"}
    assert native.axes == {"x": 1, "y": 3, "z": 0}
    assert report["plot_styles"][0]["cse"] == report["plot_styles"][0]["csf"] == -9
    assert report["plot_styles"][0]["kf"] == 9
    assert native.plots[1].writes == []
    assert not any(index == 2 and flag in {"qs", "qf", "qb", "cse", "csf", "kf", "k", "z"}
                   for index, flag in native.reads)


@pytest.mark.parametrize("flag", ["qs", "qf", "qb", "cse", "csf"])
def test_missing_required_native_readback_fails_instead_of_passing(native, flag):
    native.fail_flag = flag
    with pytest.raises(RuntimeError, match="non-finite"):
        verify.apply_personal_typography(native, [native], style())


@pytest.mark.parametrize("flag", ["c", "cse", "csf", "kf"])
def test_typography_must_preserve_line_edge_fill_and_half_fill(native, flag):
    native.corrupt_mark = flag
    with pytest.raises(RuntimeError, match="changed a template"):
        verify.apply_personal_typography(native, [native], style())


def test_bold_false_removes_only_inline_bold_and_saved_readback_rejects_conflict(native):
    verify.apply_personal_typography(native, [native], style(bold=False))
    assert native.texts[0].text == r"CO\-(2)"
    for plot in native.plots:
        plot.writes.clear()
    report = verify.apply_personal_typography(native, [native], style(bold=False), apply=False)
    assert report["passed"] and all(not p.writes for p in native.plots)
    native.texts[0].text = r"\b(CO\-(2))"
    with pytest.raises(RuntimeError, match="conflicting inline bold"):
        verify.apply_personal_typography(native, [native], style(bold=False), apply=False)


def test_column_snapshot_reads_fill_and_border_without_symbol_properties(native):
    native.plots = [Plot(native, 1, 203)]
    native.plots[0].options.update(pfb=456, pbc=789, pbw=1.4)
    state = verify._personal_plot_state(native, [native])[0]
    assert state["pfb"] == 456 and state["pbc"] == 789 and state["pbw"] == 1.4
    assert not {"cse", "csf", "kf", "k", "z"}.intersection(state)


def test_invalid_object_visibility_does_not_pass_as_hidden(native):
    native.texts[0].show = math.nan
    with pytest.raises(RuntimeError, match="non-finite"):
        verify.apply_personal_typography(native, [native], style())


def test_readonly_verification_rejects_conflicting_inline_font(native):
    verify.apply_personal_typography(native, [native], style())
    native.texts[0].text = r"\b(\f:Times New Roman(CO\-(2)))"
    with pytest.raises(RuntimeError, match="conflicting inline font"):
        verify.apply_personal_typography(native, [native], style(), apply=False)


def test_inline_bold_covers_every_legend_line_and_preserves_samples_and_subscripts(native):
    native.texts[0].text = "\\l(1) \\b(CO\\-(2))\n\\l(2) H\\-(2)O\n"
    report = verify.apply_personal_typography(native, [native], style())
    assert native.texts[0].text == "\\b(\\l(1) CO\\-(2))\n\\b(\\l(2) H\\-(2)O)\n"
    assert report["texts"][0]["bold_source"] == "inline_markup"
    native.texts[0].text = "\\b(\\l(1) CO\\-(2))\n\\l(2) H\\-(2)O\n"
    with pytest.raises(RuntimeError, match="conflicting inline bold"):
        verify.apply_personal_typography(native, [native], style(), apply=False)


def test_native_crlf_readback_keeps_line_content_and_passes_canonical_bold(native):
    native.texts[:] = [WindowsTextObject(text="\\l(1)  CO\\-(2)\r\n\\l(2) H\\-(2)O \r\n")]
    report = verify.apply_personal_typography(native, [native], style())
    expected = "\\b(\\l(1)  CO\\-(2))\r\n\\b(\\l(2) H\\-(2)O )\r\n"
    assert native.texts[0].text == expected
    assert report["texts"][0]["text"] == expected
    assert verify.apply_personal_typography(native, [native], style(), apply=False)["passed"]


@pytest.mark.parametrize("interior", [8, 9])
@pytest.mark.parametrize("edge", [-9, 33501654])
def test_original_half_filled_symbol_channels_survive_apply_and_readonly_recheck(native, interior, edge):
    # Graph1A includes an explicit first-series edge and Automatic fills;
    # exercise both its right-half interior and the original set's upper half.
    plot = native.plots[0]
    plot.options.update(kf=interior, cse=edge, csf=-9, z=15, q=0)
    before = {key: plot.options[key] for key in ("c", "cse", "csf", "kf", "k", "z", "kh", "s")}
    applied = verify.apply_personal_typography(native, [native], style())
    assert {key: applied["plot_styles"][0][key] for key in before} == before
    assert set(plot.writes) == {"-qs", "-qf", "-qb"}
    assert plot.options["q"] == 0
    plot.writes.clear()
    reopened = verify.apply_personal_typography(native, [native], style(), apply=False)
    assert reopened["plot_styles"] == applied["plot_styles"]
    assert plot.writes == []
    # Independent saved-project validation must compare this snapshot with the
    # pre-save report; the helper alone has no historical baseline argument.
    plot.options["csf"] = 999
    changed = verify.apply_personal_typography(native, [native], style(), apply=False)
    assert changed["plot_styles"] != applied["plot_styles"]
