"""Origin graph export helpers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from .safe_errors import OriginExportError
from .verify_utils import require_nonempty

if TYPE_CHECKING:
    from ..scientific_visual import AdaptiveOriginStyle


def _profile_png_settings(style: AdaptiveOriginStyle) -> tuple[float, float, float]:
    profile = getattr(style, "personal_profile", None)
    if not profile:
        raise OriginExportError("PNG profile verification requires a frozen personal profile")
    try:
        dpi = float(profile["overrides"]["png_dpi"])
        width_in = float(style.page_width_cm / 2.54)
        height_in = float(style.page_height_cm / 2.54)
    except (KeyError, TypeError, ValueError) as exc:
        raise OriginExportError("The frozen PNG export profile is incomplete") from exc
    if not all(math.isfinite(value) and value > 0 for value in (dpi, width_in, height_in)):
        raise OriginExportError("The frozen PNG export dimensions and DPI must be positive")
    return width_in, height_in, dpi


def verify_png_export(path: Path, style: AdaptiveOriginStyle) -> dict[str, Any]:
    """Read the complete native page export and its physical resolution."""
    profile = getattr(style, "personal_profile", None)
    if not profile or "png_dpi" not in profile.get("overrides", {}):
        return {"requested": False, "inherited_template_export": True}
    width_in, height_in, expected_dpi = _profile_png_settings(style)
    expected_pixels = (width_in * expected_dpi, height_in * expected_dpi)
    try:
        require_nonempty(path)
        with Image.open(path) as image:
            image_format = image.format
            pixels = image.size
            dpi = image.info.get("dpi")
            image.verify()
    except (OSError, ValueError, RuntimeError) as exc:
        raise OriginExportError(f"Origin PNG cannot be verified: {path.name}") from exc
    if image_format != "PNG":
        raise OriginExportError(f"Origin export is not a PNG image: {path.name}")
    # Origin may truncate fractional pixels; either neighboring integer is valid.
    if any(abs(actual - expected) >= 1.0 for actual, expected in zip(pixels, expected_pixels, strict=True)):
        raise OriginExportError(
            f"Origin PNG size is {pixels[0]}x{pixels[1]} px, expected the full "
            f"{width_in:g}x{height_in:g} inch page at {expected_dpi:g} dpi"
        )
    if (
        not isinstance(dpi, tuple)
        or len(dpi) != 2
        or any(not math.isfinite(value) or abs(value - expected_dpi) > 0.02 for value in dpi)
    ):
        raise OriginExportError(
            f"Origin PNG DPI metadata is {dpi!r}, expected {expected_dpi:g} dpi"
        )
    return {
        "requested": True,
        "format": image_format,
        "width_px": pixels[0],
        "height_px": pixels[1],
        "dpi_x": dpi[0],
        "dpi_y": dpi[1],
        "expected_width_in": width_in,
        "expected_height_in": height_in,
        "expected_dpi": expected_dpi,
        "margin": "page",
        "verified": True,
    }


def _native_export_page(origin: Any) -> dict[str, float]:
    values = {key: float(origin.lt_float(f"page.{prop}")) for key, prop in (
        ("width_units", "width"), ("height_units", "height"), ("resx", "resx"), ("resy", "resy"),
    )}
    if not all(math.isfinite(value) and value > 0 for value in values.values()):
        raise OriginExportError("Origin native page geometry is invalid")
    return {**values, "width_in": values["width_units"] / values["resx"],
            "height_in": values["height_units"] / values["resy"]}


def export_graph(
    origin,
    graph,
    output_png: Path,
    output_pdf: Path,
    output_tif: Path | None = None,
    *,
    raster_width: int = 2100,
    style: AdaptiveOriginStyle | None = None,
) -> dict[str, bool]:
    result: dict[str, bool] = {}
    profile = getattr(style, "personal_profile", None) if style is not None else None
    if profile and "png_dpi" in profile.get("overrides", {}):
        width_in, height_in, dpi = _profile_png_settings(style)
        output_png.unlink(missing_ok=True)
        graph.activate()
        native_page = _native_export_page(origin)
        width_px = round(width_in * dpi)
        # Origin 2021 GraphicalExport.c reads raster DPI from tr2.<format>.DotsPerInch.
        # Its GetProperSize rounds the derived dimension to two decimals (lines
        # 139, 2594): inches turn 7.933 into 7.93. Unit=2 keeps that rounding in
        # pixels instead. Margin=2 retains the complete physical page and aspect.
        png_command = (
            f'expGraph type:=png export:=page filename:="{output_png.stem}" '
            f'path:="{output_png.parent.as_posix()}" overwrite:=replace sysopts:=0 keepsize:=0 '
            f"tr.Margin:=2 tr1.Unit:=2 tr1.Rescaling:=0 tr1.Width:={width_px} "
            f"tr2.PNG.DotsPerInch:={dpi:g};"
        )
        if not origin.lt_exec(png_command):
            raise OriginExportError(f"Origin did not export {output_png.name} with the frozen PNG profile")
        graph.activate()
        if _native_export_page(origin) != native_page:
            raise OriginExportError("Origin PNG export changed the native page geometry")
        verify_png_export(output_png, style)
        result["png"] = True
    else:
        ok = graph.save_fig(str(output_png), type=output_png.suffix[1:].lower(), width=raster_width)
        if not ok:
            raise OriginExportError(f"Origin did not export {output_png.name}")
        try:
            require_nonempty(output_png)
        except RuntimeError as exc:
            raise OriginExportError(str(exc)) from exc
        result["png"] = True

    output_pdf.unlink(missing_ok=True)
    graph.activate()
    pdf_command = (
        f'expGraph type:=pdf export:=page filename:="{output_pdf.stem}" '
        f'path:="{output_pdf.parent.as_posix()}" overwrite:=replace sysopts:=0 keepsize:=1 '
        "tr.Margin:=2 tr2.PDF.Fonts.Embed:=1 tr2.PDF.Fonts.TrueType:=1;"
    )
    if not origin.lt_exec(pdf_command):
        raise OriginExportError(f"Origin did not export {output_pdf.name} with embedded fonts")
    try:
        require_nonempty(output_pdf)
    except RuntimeError as exc:
        raise OriginExportError(str(exc)) from exc
    if b"/FontFile" not in output_pdf.read_bytes():
        raise OriginExportError(f"Origin PDF does not contain embedded fonts: {output_pdf.name}")
    result["pdf"] = True

    if output_tif is not None:
        ok = graph.save_fig(str(output_tif), type="tif", width=raster_width)
        if not ok:
            raise OriginExportError(f"Origin did not export {output_tif.name}")
        try:
            require_nonempty(output_tif)
        except RuntimeError as exc:
            raise OriginExportError(str(exc)) from exc
        result["tif"] = True
    return result
