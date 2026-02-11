import numpy as np

from spectral_edge.batch.config import BatchConfig, ReferenceCurveConfig
from spectral_edge.batch.powerpoint_output import _create_psd_plot
from spectral_edge.utils.reference_curves import prepare_reference_curves_for_plot


def test_prepare_reference_curves_for_plot_clips_and_skips_invalid():
    curves = [
        {
            "name": "Valid Curve",
            "frequencies": [10.0, 20.0, 80.0, 800.0, 2500.0],
            "psd": [0.01, 0.02, 0.05, 0.05, 0.01],
            "enabled": True,
            "source": "imported",
            "line_style": "dashed",
        },
        {
            "name": "Invalid Curve",
            "frequencies": [10.0],
            "psd": [0.01],
            "enabled": True,
            "source": "imported",
        },
    ]

    prepared = prepare_reference_curves_for_plot(curves, freq_min=20.0, freq_max=2000.0)
    assert len(prepared) == 1
    assert prepared[0]["name"] == "Valid Curve"
    assert np.all(prepared[0]["frequencies"] >= 20.0)
    assert np.all(prepared[0]["frequencies"] <= 2000.0)


def test_prepare_reference_curves_for_plot_can_preserve_full_curve_range():
    curves = [
        {
            "name": "Valid Curve",
            "frequencies": [10.0, 20.0, 80.0, 800.0, 2500.0],
            "psd": [0.01, 0.02, 0.05, 0.05, 0.01],
            "enabled": True,
            "source": "imported",
            "line_style": "dashed",
        }
    ]

    prepared = prepare_reference_curves_for_plot(
        curves,
        freq_min=20.0,
        freq_max=2000.0,
        clip_to_range=False,
    )
    assert len(prepared) == 1
    assert prepared[0]["name"] == "Valid Curve"
    assert prepared[0]["frequencies"][0] == 10.0
    assert prepared[0]["frequencies"][-1] == 2500.0


def test_create_psd_plot_with_reference_curves_returns_image_bytes():
    config = BatchConfig()
    config.psd_config.frequency_spacing = "constant_bandwidth"
    config.psd_config.freq_min = 20.0
    config.psd_config.freq_max = 2000.0
    config.display_config.psd_show_legend = True
    config.powerpoint_config.reference_curves = [
        ReferenceCurveConfig(
            name="Minimum Screening",
            frequencies=[20.0, 80.0, 800.0, 2000.0],
            psd=[0.01, 0.04, 0.04, 0.01],
            enabled=True,
            source="builtin",
            builtin_id="minimum_screening",
            line_style="dashed",
        ),
        ReferenceCurveConfig(
            name="Broken Curve",
            frequencies=[50.0],
            psd=[0.02],
            enabled=True,
            source="imported",
            line_style="dashed",
        ),
    ]

    event_result = {
        "frequencies": np.array([20.0, 40.0, 80.0, 160.0, 320.0, 640.0, 1280.0, 2000.0]),
        "psd": np.array([0.02, 0.03, 0.05, 0.06, 0.05, 0.04, 0.03, 0.02]),
    }

    image_bytes = _create_psd_plot(
        event_result=event_result,
        config=config,
        units="g",
        plot_title="PSD Test",
        layout="psd_only",
        slot_role="single",
    )
    assert isinstance(image_bytes, (bytes, bytearray))
    assert len(image_bytes) > 0
