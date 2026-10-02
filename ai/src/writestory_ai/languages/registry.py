from writestory_ai.languages.base import LanguagePack
from writestory_ai.languages.vi import VietnamesePack

_PACKS: dict[str, LanguagePack] = {"vi": VietnamesePack()}

SUPPORTED_LANGUAGES: tuple[str, ...] = tuple(_PACKS)


class UnsupportedLanguageError(ValueError):
    pass


def get_language_pack(code: str) -> LanguagePack:
    try:
        return _PACKS[code]
    except KeyError:
        raise UnsupportedLanguageError(
            f"Ngôn ngữ '{code}' chưa có gói; MVP chỉ hỗ trợ: {', '.join(SUPPORTED_LANGUAGES)}"
        ) from None
