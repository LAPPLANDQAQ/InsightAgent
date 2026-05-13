"""Streamlit helper tests."""

from frontend.streamlit_app import _poll_timed_out, _radar_svg


def test_poll_timeout_helper():
    assert not _poll_timed_out(100.0, 109.0, 10)
    assert _poll_timed_out(100.0, 110.0, 10)


def test_radar_svg_includes_escaped_table():
    svg = _radar_svg(
        [
            {"dimension": "<pricing>", "evidence_count": 2, "sufficient": True},
            {"dimension": "features", "evidence_count": 0, "sufficient": False},
        ]
    )

    assert "Dimension" in svg
    assert "Evidence Count" in svg
    assert "Sufficient" in svg
    assert "Needs Improvement" in svg
    assert "&lt;pricing&gt;" in svg
    assert "<pricing>" not in svg
