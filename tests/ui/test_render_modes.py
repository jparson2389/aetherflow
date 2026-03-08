from aetherflow.ui.panels.render_mode_panel import RenderModePanelModel


def test_render_modes_present_latency_tradeoffs() -> None:
    panel = RenderModePanelModel.default()

    assert [mode.mode_id for mode in panel.modes] == ["render.cpu", "render.gpu"]
    assert panel.modes[0].latency_priority == "lowest"
