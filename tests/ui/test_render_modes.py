"""Render mode panel UI model tests."""

import pytest

from aetherflow.ui.panels.render_mode_panel import RenderModePanelModel


def test_render_modes_present_latency_tradeoffs() -> None:
    """Default render modes expose CPU vs GPU with latency tradeoffs."""
    panel = RenderModePanelModel.default()

    assert [mode.mode_id for mode in panel.modes] == ['render.cpu', 'render.gpu']
    assert panel.modes[0].latency_priority == 'lowest'
    assert panel.modes[1].requires_restart is True


def test_render_modes_have_cpu_load_description() -> None:
    """Each render mode describes its CPU load impact."""
    panel = RenderModePanelModel.default()

    assert panel.modes[0].cpu_load == 'highest'
    assert panel.modes[1].cpu_load == 'lower'


def test_render_mode_selection_default_is_cpu() -> None:
    """Default active render mode is CPU."""
    panel = RenderModePanelModel.default()

    assert panel.active_mode_id == 'render.cpu'


def test_render_mode_selection_switch_to_gpu() -> None:
    """Switching to GPU render mode updates the active mode."""
    panel = RenderModePanelModel.default()
    updated = panel.select('render.gpu')

    assert updated.active_mode_id == 'render.gpu'


def test_render_mode_selection_invalid_mode_raises() -> None:
    """Selecting a nonexistent mode raises ValueError."""
    panel = RenderModePanelModel.default()

    with pytest.raises(ValueError, match=r'render\.nonexistent'):
        panel.select('render.nonexistent')


def test_render_mode_panel_gpu_requires_restart() -> None:
    """GPU render mode signals that a restart is required."""
    panel = RenderModePanelModel.default()
    gpu = next(m for m in panel.modes if m.mode_id == 'render.gpu')
    assert gpu.requires_restart is True

    cpu = next(m for m in panel.modes if m.mode_id == 'render.cpu')
    assert cpu.requires_restart is False
