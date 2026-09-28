from app.core.config import Settings, settings


def test_settings_default_app_name():
    assert settings.app_name == "Kabadi Mitra API"


def test_settings_is_a_settings_instance():
    assert isinstance(settings, Settings)
