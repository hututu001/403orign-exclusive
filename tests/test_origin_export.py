from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

RUNTIME_SRC = Path(__file__).resolve().parents[1] / "runtime" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from origin_sciplot.origin_backend.export_utils import export_graph, verify_png_export  # noqa: E402
from origin_sciplot.origin_backend.safe_errors import OriginExportError  # noqa: E402


def _style(overrides=None, *, width_in=0.2, height_in=0.15):
    return SimpleNamespace(
        page_width_cm=width_in * 2.54,
        page_height_cm=height_in * 2.54,
        personal_profile={"overrides": {"png_dpi": 600} if overrides is None else overrides},
    )


def _png(path, size=(120, 90), dpi=600):
    options = {} if dpi is None else {"dpi": (dpi, dpi)}
    Image.new("RGB", size, "white").save(path, **options)


def test_png_verification_reads_real_pixels_and_phys_metadata(tmp_path):
    path = tmp_path / "result.png"
    _png(path)
    result = verify_png_export(path, _style())
    assert result["verified"] is True
    assert (result["width_px"], result["height_px"]) == (120, 90)
    assert result["dpi_x"] == pytest.approx(600, abs=0.02)
    assert result["dpi_y"] == pytest.approx(600, abs=0.02)


@pytest.mark.parametrize("size,dpi,message", [
    ((110, 90), 600, "size"),
    ((120, 90), 300, "DPI metadata"),
    ((120, 90), None, "DPI metadata"),
])
def test_png_verification_rejects_crop_wrong_dpi_and_missing_dpi(tmp_path, size, dpi, message):
    path = tmp_path / "result.png"
    _png(path, size, dpi)
    with pytest.raises(OriginExportError, match=message):
        verify_png_export(path, _style())


@pytest.mark.parametrize("height_px", [89, 90])
def test_png_verification_allows_native_fractional_pixel_rounding(tmp_path, height_px):
    path = tmp_path / "result.png"
    _png(path, (120, height_px))
    assert verify_png_export(path, _style(height_in=89.8 / 600))["verified"]


class _Graph:
    def __init__(self):
        self.saved = []

    def activate(self):
        pass

    def save_fig(self, path, **options):
        self.saved.append((Path(path), options))
        Path(path).write_bytes(b"legacy export")
        return path


class _Origin:
    def __init__(self, png, pdf, *, size=None, dpi=600, native_inches=(0.2, 0.15)):
        self.png = png
        self.pdf = pdf
        self.size = size
        self.dpi = dpi
        self.commands = []
        self.native_inches = native_inches

    def lt_float(self, expression):
        return {"page.width": self.native_inches[0] * 600,
                "page.height": self.native_inches[1] * 600, "page.resx": 600, "page.resy": 600}[expression]

    def lt_exec(self, command):
        self.commands.append(command)
        if "type:=png" in command:
            match = re.search(r"tr1\.(Width|Height):=([0-9.]+)", command)
            dimension, value = match[1], float(match[2])
            native_width, native_height = self.native_inches
            size = self.size or ((round(value), round(value * native_height / native_width))
                                     if dimension == "Width" else
                                     (round(value * native_width / native_height), round(value)))
            _png(self.png, size, self.dpi)
            with Image.open(self.png) as raw:
                image = raw.convert("RGBA")
                image.putpixel((0, 0), (11, 73, 191, 255))
                image.putpixel((size[0] // 2, size[1] // 2), (231, 27, 95, 255))
                self.raw_pixels = image.tobytes()
                image.save(self.png, dpi=(self.dpi, self.dpi))
        else:
            self.pdf.write_bytes(b"%PDF /FontFile test embedded font")
        return True


def test_profile_export_uses_native_png_dpi_and_preserves_other_exports(tmp_path):
    png, pdf, tif = (tmp_path / name for name in ("result.png", "result.pdf", "result.tif"))
    graph, origin = _Graph(), _Origin(png, pdf)
    result = export_graph(origin, graph, png, pdf, tif, style=_style())
    assert result == {"png": True, "pdf": True, "tif": True}
    assert all(type(value) is bool for value in result.values())
    assert "tr2.PNG.DotsPerInch:=600" in origin.commands[0]
    assert "tr1.Unit:=2" in origin.commands[0]
    assert "tr1.Rescaling:=0" in origin.commands[0]
    assert "tr1.Width:=120 " in origin.commands[0]
    assert "tr.Margin:=2" in origin.commands[0]
    assert "tr.Advanced.DPI" not in origin.commands[0]
    assert graph.saved == [(tif, {"type": "tif", "width": 2100})]


@pytest.mark.parametrize("style", [None, _style({}), _style({"axis_title_size_pt": 28})])
def test_unrequested_png_profile_keeps_legacy_export(tmp_path, style):
    png, pdf = tmp_path / "result.png", tmp_path / "result.pdf"
    graph, origin = _Graph(), _Origin(png, pdf)
    result = export_graph(origin, graph, png, pdf, raster_width=1800, style=style)
    assert result == {"png": True, "pdf": True}
    assert graph.saved == [(png, {"type": "png", "width": 1800})]
    assert len(origin.commands) == 1
    assert "type:=pdf" in origin.commands[0]
    if style is not None:
        assert verify_png_export(png, style) == {
            "requested": False, "inherited_template_export": True,
        }


def test_profile_export_rejects_wrong_native_dpi_before_pdf(tmp_path):
    png, pdf = tmp_path / "result.png", tmp_path / "result.pdf"
    graph, origin = _Graph(), _Origin(png, pdf, dpi=300)
    with pytest.raises(OriginExportError, match="DPI metadata"):
        export_graph(origin, graph, png, pdf, style=_style())
    assert not pdf.exists()
    assert not graph.saved


def test_single_run_dpi_override_is_used_without_default_600(tmp_path):
    png, pdf = tmp_path / "result.png", tmp_path / "result.pdf"
    graph, origin = _Graph(), _Origin(png, pdf, size=(60, 45), dpi=300)
    export_graph(origin, graph, png, pdf, style=_style({"png_dpi": 300}))
    assert "tr2.PNG.DotsPerInch:=300" in origin.commands[0]
    assert "tr1.Unit:=2" in origin.commands[0]
    assert "tr1.Width:=60 " in origin.commands[0]
    assert verify_png_export(png, _style({"png_dpi": 300}))["expected_dpi"] == 300


@pytest.mark.parametrize("height_px,valid", [(4758, False), (4759, True), (4760, True)])
def test_physical_page_gate_rejects_origin_inch_precision_loss(tmp_path, height_px, valid):
    png, pdf = tmp_path / "result.png", tmp_path / "result.pdf"
    graph, origin = _Graph(), _Origin(png, pdf, size=(6816, height_px), native_inches=(11.36, 7.933))
    style = _style(width_in=11.36, height_in=7.933)
    if valid:
        export_graph(origin, graph, png, pdf, style=style)
        assert verify_png_export(png, style)["expected_height_in"] == pytest.approx(7.933)
    else:
        with pytest.raises(OriginExportError, match="size"):
            export_graph(origin, graph, png, pdf, style=style)
        assert not pdf.exists()
    assert "tr1.Unit:=2 tr1.Rescaling:=0 tr1.Width:=6816 " in origin.commands[0]
    assert "tr.Margin:=2" in origin.commands[0]
    assert "tr2.PNG.DotsPerInch:=600" in origin.commands[0]


@pytest.mark.parametrize("native_inches,content", [
    ((0.4, 0.2), (240, 120)), ((0.1, 0.2), (60, 120)),
])
def test_native_page_export_preserves_aspect_and_pixels_without_a_second_canvas(
    tmp_path, native_inches, content,
):
    png, pdf = tmp_path / "result.png", tmp_path / "result.pdf"
    graph, origin = _Graph(), _Origin(png, pdf, native_inches=native_inches)
    style = _style(width_in=native_inches[0], height_in=native_inches[1])
    before = {key: origin.lt_float(key) for key in ("page.width", "page.height", "page.resx", "page.resy")}
    export_graph(origin, graph, png, pdf, style=style)
    assert f"tr1.Width:={content[0]} " in origin.commands[0]
    assert "tr1.Rescaling:=0" in origin.commands[0]
    report = verify_png_export(png, style)
    assert (report["width_px"], report["height_px"]) == content
    assert before == {key: origin.lt_float(key) for key in before}
    with Image.open(png) as image:
        assert image.convert("RGBA").tobytes() == origin.raw_pixels


def test_native_aspect_distortion_is_rejected(tmp_path):
    png, pdf = tmp_path / "result.png", tmp_path / "result.pdf"
    origin = _Origin(png, pdf, native_inches=(0.4, 0.2), size=(120, 90))
    style = _style(width_in=0.4, height_in=0.2)
    with pytest.raises(OriginExportError, match="size"):
        export_graph(origin, _Graph(), png, pdf, style=style)
    assert not pdf.exists()
