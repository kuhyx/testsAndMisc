"""MoviePy visualization for PYTANIE 23: Image Segmentation.

Thin orchestrator that assembles sections from submodules into
the final video.
"""

from __future__ import annotations

from moviepy import VideoClip, concatenate_videoclips

from python_pkg.praca_magisterska_video._q23_classical import (
    _region_growing_demo,
    _segmentation_concept,
    _thresholding_demo,
    _watershed_demo,
)
from python_pkg.praca_magisterska_video._q23_deeplab import _deeplab_demo
from python_pkg.praca_magisterska_video._q23_helpers import (
    FPS,
    OUTPUT,
    _logger,
    _make_header,
)
from python_pkg.praca_magisterska_video._q23_transformer import (
    _methods_comparison,
    _transformer_seg_demo,
)
from python_pkg.praca_magisterska_video._q23_unet_fcn import _fcn_demo, _unet_demo


def main() -> None:
    """Generate the Q23 segmentation visualization video."""
    sections: list[VideoClip] = []

    sections.append(
        _make_header(
            "Pytanie 23: Segmentacja obrazu",
            "Problem, strategie klasyczne i sieci neuronowe",
            duration=4.0,
        )
    )

    # Concept
    sections.append(_make_header("Co to segmentacja?", "Etykieta klasy per piksel"))
    sections.extend(_segmentation_concept())

    # Thresholding
    sections.append(
        _make_header("Progowanie + Otsu", "Najprostsza metoda — automatyczny próg")
    )
    sections.extend(_thresholding_demo())

    # Region Growing
    sections.append(_make_header("Region Growing", "Seed → BFS do podobnych sąsiadów"))
    sections.extend(_region_growing_demo())

    # Watershed
    sections.append(_make_header("Watershed", "Obraz jako mapa topograficzna"))
    sections.extend(_watershed_demo())

    # FCN
    sections.append(
        _make_header("FCN (Deep Learning)", "Fully Convolutional Network — Conv 1x1")
    )
    sections.extend(_fcn_demo())

    # U-Net
    sections.append(
        _make_header(
            "U-Net (Deep Learning)", "Architektura encoder-decoder + skip concat"
        )
    )
    sections.extend(_unet_demo())

    # DeepLab
    sections.append(
        _make_header(
            "DeepLab v3+ (Deep Learning)", "Dilated convolution + ASPP — multi-scale"
        )
    )
    sections.extend(_deeplab_demo())

    # Transformer segmentation
    sections.append(
        _make_header(
            "Transformer (SegFormer, Mask2Former)", "Self-attention — globalny kontekst"
        )
    )
    sections.extend(_transformer_seg_demo())

    # Comparison
    sections.append(_methods_comparison())

    # Summary
    sections.append(
        _make_header(
            "Podsumowanie",
            "Klasyczne: próg/region/watershed | DL: FCN/U-Net/DeepLab/Transformer",
            duration=4.0,
        )
    )

    final = concatenate_videoclips(sections, method="compose")
    final.write_videofile(
        OUTPUT, fps=FPS, codec="libx264", audio=False, preset="medium", threads=4
    )
    _logger.info("Video saved to: %s", OUTPUT)


if __name__ == "__main__":
    main()
