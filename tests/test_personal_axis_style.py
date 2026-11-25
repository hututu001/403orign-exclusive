import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime/src'))
from origin_sciplot.origin_backend.verify_utils import apply_personal_axes  # noqa: E402
from origin_sciplot.scientific_visual import (  # noqa: E402
    PersonalProfileError,
    apply_personal_profile,
    normalize_personal_profile,
    personal_axis_style,
)
from origin_sciplot.scientific_workflow import prepare_scientific  # noqa: E402

PROFILE = {'id': 'n4-f-u-v1.2', 'overrides': {
    'frame_line_width_pt': 3, 'major_tick_length_pt': 8, 'axis_color': '#000000',
    'tick_direction': 'out', 'numeric_minor_ticks': 1, 'tick_details': 'auto',
    'axis_frame': 'four_sides',
}}

@pytest.mark.parametrize('template', ['bar', 'trend', 'line_error', 'horizontal_bar'])
def test_axis_profile_preserves_data_scales_and_template_colors(template):
    before = prepare_scientific(ROOT / 'runtime/templates' / template / 'example_standard.csv', template)
    after, report = apply_personal_profile(before, PROFILE)
    assert before.source_sha256 == after.source_sha256
    assert before.plot_spec.series == after.plot_spec.series
    assert before.plot_spec.axis_plan == after.plot_spec.axis_plan
    old, new = before.plot_spec.display_plan.figure_style, after.plot_spec.display_plan.figure_style
    assert new.palette_name == old.palette_name
    assert new.frame_line_width_pt == 3 and new.major_tick_length_pt == 8
    assert personal_axis_style(new) == PROFILE['overrides']
    assert set(report['applied_fields']) == set(PROFILE['overrides'])

@pytest.mark.parametrize('template', ['heatmap', 'event_raster', 'signal_stack', 'pie'])
def test_specialized_axes_keep_their_template_contract(template):
    before = prepare_scientific(ROOT / 'runtime/templates' / template / 'example_standard.csv', template)
    after, report = apply_personal_profile(before, PROFILE)
    a,b = asdict(before.plot_spec.display_plan.figure_style),asdict(after.plot_spec.display_plan.figure_style)
    a.pop("personal_profile")
    b.pop("personal_profile")
    assert a == b
    assert personal_axis_style(after.plot_spec.display_plan.figure_style) == {}
    assert report['applied_fields'] == []

@pytest.mark.parametrize(
    'key,value', [
        ('frame_line_width_pt', 0), ('tick_direction', 'both'),
        ('numeric_minor_ticks', 1.5), ('tick_details', 4),
    ]
)
def test_invalid_axis_fields_fail(key,value):
    with pytest.raises(PersonalProfileError):
        normalize_personal_profile({'id':'bad','overrides':{key:value}})

class AxisLayer:
    def __init__(self):
        self.obj=self
        self.state={f'{a}.{k}':v for a in ('x','y','x2','y2') for k,v in {
            'showLabels':1,'showAxes':3,'from':0,'to':40,'inc':10,'type':0,
            'label.type':1,'thickness':1.3,'color':1,'ticklength':5.5,'ticks':5,'minorTicks':0,'showGrids':0}.items()}
        self.state['x.label.type']=2
    def activate(self): pass
    def lt_float(self,key): return self.state[key.removeprefix('layer.')]
    def LT_execute(self,cmd):
        key,value=cmd.removeprefix('layer.').rstrip(';').split('=')
        self.state[key]=float(value)
        return True

def test_native_axis_verifier_is_readonly_and_rejects_wrong_direction(monkeypatch):
    from types import SimpleNamespace

    from origin_sciplot.origin_backend import verify_utils
    layer=AxisLayer()
    monkeypatch.setattr(verify_utils,'_personal_tick_auto_details',lambda *args,**kwargs:{'mode':'auto'})
    style=SimpleNamespace(profile_name='adaptive-bar-bar_error',personal_profile=PROFILE)
    result=apply_personal_axes(layer,[layer],style)
    assert layer.state['x.minorTicks']==0
    assert layer.state['y.minorTicks']==1
    assert layer.state['x2.ticks']==layer.state['y2.ticks']==0
    assert layer.state['x.ticks']==layer.state['y.ticks']==10
    before=layer.state.copy()
    assert apply_personal_axes(layer,[layer],style,apply=False)==result
    assert layer.state==before
    layer.state['y.ticks']=5
    with pytest.raises(RuntimeError,match='readback mismatch'):
        apply_personal_axes(layer,[layer],style,apply=False)


def test_preview_axis_strokes_and_outward_ticks_keep_category_positions():
    from origin_sciplot.scientific_preview import PREVIEW_WIDTH_IN, _build_scientific_preview_figure
    base=prepare_scientific(ROOT/'examples/gallery/bar_grouped_error.csv','bar')
    updated,_=apply_personal_profile(base,PROFILE)
    fig=_build_scientific_preview_figure(updated)
    try:
        ax=fig.axes[0]
        scale=PREVIEW_WIDTH_IN/(updated.plot_spec.display_plan.figure_style.page_width_cm/2.54)
        assert ax.spines['left'].get_linewidth()==pytest.approx(3*scale)
        assert ax.xaxis.majorTicks[0].get_tickdir()=='out'
        assert ax.xaxis.majorTicks[0].tick1line.get_markersize()==pytest.approx(8*scale)
        assert list(ax.get_xticks())==[0,1,2,3,4]
    finally:
        fig.clear()
