from app.core.config import Settings


def test_cors_origins_are_parsed_from_csv() -> None:
    settings = Settings(
        cors_allowed_origins="https://rag.example.com, http://127.0.0.1:8501, ,"
    )

    assert settings.cors_origins == [
        "https://rag.example.com",
        "http://127.0.0.1:8501",
    ]


def test_cors_can_be_disabled_for_private_api() -> None:
    settings = Settings(cors_allowed_origins="")

    assert settings.cors_origins == []
