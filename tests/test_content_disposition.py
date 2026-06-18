"""Tests for the Content-Disposition header helper."""

from __future__ import annotations

from backend.app.content_disposition import make_content_disposition, _to_ascii_safe, _encode_rfc5987


def test_ascii_safe_preserves_english_name():
    result = _to_ascii_safe("MyPatent")
    assert result == "MyPatent"


def test_ascii_safe_strips_chinese_characters():
    result = _to_ascii_safe("一种图像缺陷识别方法")
    # All non-ASCII stripped; only safe chars remain.
    assert all(ord(c) < 128 for c in result)


def test_ascii_safe_sanitizes_illegal_chars():
    result = _to_ascii_safe('test<>:"file')
    assert ">" not in result
    assert "<" not in result
    assert '"' not in result
    assert ":" not in result


def test_ascii_safe_handles_empty():
    result = _to_ascii_safe("")
    assert result == "download"


def test_ascii_safe_handles_only_illegal_chars():
    result = _to_ascii_safe('<>:"/\\|?*')
    assert result == "download"


def test_encode_rfc5987_chinese():
    # 中文 -> UTF-8 bytes -> percent-encoded
    encoded = _encode_rfc5987("中文")
    # 中 = E4 B8 AD, 文 = E6 96 87
    assert encoded == "%E4%B8%AD%E6%96%87"


def test_encode_rfc5987_ascii():
    encoded = _encode_rfc5987("hello.txt")
    assert encoded == "hello.txt"  # safe chars not encoded


def test_encode_rfc5987_special_chars():
    encoded = _encode_rfc5987("file name.txt")
    # space = %20
    assert encoded == "file%20name.txt"


def test_make_cd_header_with_chinese_name():
    header = make_content_disposition("一种图像缺陷识别方法.docx")
    assert header.startswith("attachment; filename=\"")
    assert "; filename*=UTF-8''" in header
    # ASCII fallback should have no Chinese characters
    ascii_part = header.split("; filename=")[1].split(";")[0].strip('"')
    assert all(ord(c) < 128 for c in ascii_part)
    # Extension preserved in ASCII part
    assert ascii_part.endswith(".docx")
    # UTF-8 encoded name also ends with .docx
    assert "UTF-8''%E4%B8%80" in header  # 一种... encoded


def test_make_cd_header_preserves_extension():
    header = make_content_disposition("project.docx")
    assert 'filename="project.docx"' in header
    # The filename*= clause contains UTF-8''project.docx
    assert "UTF-8''project.docx" in header


def test_make_cd_header_strips_path_components():
    header = make_content_disposition("/some/path/to/file.docx")
    assert "path" not in header
    assert "/some" not in header
    # Should only contain "file.docx"
    assert "file.docx" in header


def test_make_cd_header_strips_windows_separators():
    header = make_content_disposition("C:\\Users\\test\\file.docx")
    assert "Users" not in header
    assert "test\\" not in header.replace("%27", "")
    # Should only contain "file.docx"
    assert "file.docx" in header


def test_make_cd_header_with_explicit_extension():
    header = make_content_disposition("project", extension="docx")
    assert "project.docx" in header


def test_make_cd_header_override_extension():
    header = make_content_disposition("project.txt", extension="docx")
    assert "project.docx" in header
    assert ".txt" not in header


def test_make_cd_header_sanitizes_illegal_filename_chars():
    header = make_content_disposition('test<>:"file.docx')
    assert ">" not in header.split("filename=")[1].split(";")[0]
    assert "<" not in header.split("filename=")[1].split(";")[0]
