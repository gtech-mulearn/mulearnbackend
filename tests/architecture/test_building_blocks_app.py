from pathlib import Path

from django.apps import apps


def test_building_blocks_is_an_installed_app():
    config = apps.get_app_config("building_blocks")

    assert type(config).__name__ == "BuildingBlocksConfig"
    assert Path(config.path).name == "building_blocks"
