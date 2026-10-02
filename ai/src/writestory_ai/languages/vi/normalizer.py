import re
import unicodedata

# Khoảng trắng đặc biệt hay gặp khi dán từ Word/web: NBSP, en/em space…, narrow NBSP, ideographic.
_SPACE_LIKE = re.compile("[\u00a0\u2000-\u200a\u202f\u205f\u3000]")
# Zero-width space/joiner/non-joiner và BOM.
_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\ufeff]")
_TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)


def normalize_text(text: str) -> str:
    """Chuẩn hóa văn bản tiếng Việt khi lưu/dán (Plan §6.6).

    - Unicode NFC (dữ liệu dán từ nguồn ngoài thường ở dạng NFD hoặc tổ hợp).
    - Xuống dòng về `\\n`; bỏ ký tự zero-width; khoảng trắng đặc biệt thành dấu cách thường.
    - Bỏ khoảng trắng cuối dòng.

    Không đổi kiểu bỏ dấu (hoà/hòa) – đó là quyết định theo `style_profile` (F08).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _ZERO_WIDTH.sub("", text)
    text = _SPACE_LIKE.sub(" ", text)
    text = _TRAILING_SPACE.sub("", text)
    return unicodedata.normalize("NFC", text)
