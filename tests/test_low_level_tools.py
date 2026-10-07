"""Tests for low-level PDF object/stream tools."""

import pytest
import pymupdf

from mcp.server.mcpserver.exceptions import ToolError
from pdform_mcp.tools import (
    low_level_create_indirect_object,
    low_level_create_indirect_object_as_json,
    low_level_read_object,
    low_level_read_object_value,
    low_level_read_stream,
    low_level_set_object_value,
    low_level_set_object_value_as_json,
    low_level_write_object,
    low_level_write_object_as_json,
    low_level_write_stream,
)
from pdform_mcp.tools.low_level_tools import _json_to_pdf, _json_to_pdf_name


def make_pdf(path):
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    return str(path)


class TestLowLevelWriteObject:
    def test_overwrites_whole_object(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = int(low_level_create_indirect_object(path).rsplit(" ", 1)[1])

        assert low_level_write_object(path, xref, "<< /Foo /Bar >>") == "Value set successfully"

        obj = low_level_read_object(path, xref)
        assert "/Foo" in obj and "/Bar" in obj

    def test_overwrite_replaces_existing_keys(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = int(low_level_create_indirect_object(path, "<< /Old 1 >>").rsplit(" ", 1)[1])

        low_level_write_object(path, xref, "<< /New 2 >>")

        obj = low_level_read_object(path, xref)
        assert "/New" in obj
        assert "/Old" not in obj

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_write_object(str(tmp_path / "missing.pdf"), 1, "<<>>")


class TestLowLevelWriteStream:
    def test_writes_stream_and_reports_it(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = int(low_level_create_indirect_object(path).rsplit(" ", 1)[1])

        result = low_level_write_stream(path, xref, b"hello stream")

        assert "created" not in result.lower()
        assert str(xref) in result
        assert low_level_read_stream(path, xref) == b"hello stream"

    def test_overwrites_existing_stream(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = int(low_level_create_indirect_object(path, "<<>>", b"first").rsplit(" ", 1)[1])

        low_level_write_stream(path, xref, b"second")

        assert low_level_read_stream(path, xref) == b"second"

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_write_stream(str(tmp_path / "missing.pdf"), 1, b"x")


def new_xref(path, value="<<>>", stream=None):
    return int(low_level_create_indirect_object(path, value, stream).rsplit(" ", 1)[1])


class TestLowLevelReadObject:
    def test_reads_object_by_xref(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path, "<< /Foo /Bar >>")

        obj = low_level_read_object(path, xref)
        assert "/Foo" in obj and "/Bar" in obj

    def test_none_reads_catalog(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")

        assert "/Catalog" in low_level_read_object(path, None)

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_read_object(str(tmp_path / "missing.pdf"), 1)


class TestLowLevelReadStream:
    def test_reads_stream(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path, "<<>>", b"data")

        assert low_level_read_stream(path, xref) == b"data"

    def test_object_without_stream_returns_none(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        assert low_level_read_stream(path, xref) is None

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_read_stream(str(tmp_path / "missing.pdf"), 1)


class TestLowLevelReadObjectValue:
    def test_reads_typed_value(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path, "<< /Foo /Bar /Num 5 >>")

        assert low_level_read_object_value(path, xref, "Foo") == ("name", "/Bar")
        assert low_level_read_object_value(path, xref, "Num") == ("int", "5")

    def test_none_reads_from_catalog(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")

        assert low_level_read_object_value(path, None, "Type") == ("name", "/Catalog")

    def test_missing_key_is_null(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        assert low_level_read_object_value(path, xref, "Nope")[0] == "null"

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_read_object_value(str(tmp_path / "missing.pdf"), 1, "Foo")


class TestLowLevelSetObjectValue:
    def test_sets_key_preserving_others(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path, "<< /Keep 1 >>")

        assert low_level_set_object_value(path, xref, "New", "/Val") == "Value set successfully"

        assert low_level_read_object_value(path, xref, "New") == ("name", "/Val")
        assert low_level_read_object_value(path, xref, "Keep") == ("int", "1")

    def test_nested_path_creates_intermediates(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        low_level_set_object_value(path, xref, "A/B", "7")

        assert low_level_read_object_value(path, xref, "A/B") == ("int", "7")

    def test_none_targets_catalog(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")

        low_level_set_object_value(path, None, "Custom", "42")

        assert low_level_read_object_value(path, None, "Custom") == ("int", "42")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_set_object_value(str(tmp_path / "missing.pdf"), 1, "K", "1")


class TestLowLevelSetObjectValueAsJson:
    def test_sets_json_value(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        low_level_set_object_value_as_json(path, xref, "N", 3)
        low_level_set_object_value_as_json(path, xref, "Flag", True)
        low_level_set_object_value_as_json(path, xref, "Nm", "/Yep")

        assert low_level_read_object_value(path, xref, "N") == ("int", "3")
        assert low_level_read_object_value(path, xref, "Flag") == ("bool", "true")
        assert low_level_read_object_value(path, xref, "Nm") == ("name", "/Yep")

    def test_sets_nested_structures(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        low_level_set_object_value_as_json(path, xref, "D", {"/X": [1, 2], "/R": "xref:5"})

        assert low_level_read_object_value(path, xref, "D/X")[1].replace(" ", "") == "[12]"
        assert low_level_read_object_value(path, xref, "D/R") == ("xref", "5 0 R")

    def test_unconvertible_string_raises_tool_error(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        with pytest.raises(ToolError, match="cannot be converted"):
            low_level_set_object_value_as_json(path, xref, "K", "plain string")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_set_object_value_as_json(str(tmp_path / "missing.pdf"), 1, "K", 1)


class TestLowLevelWriteObjectAsJson:
    def test_overwrites_with_json_object(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        low_level_write_object_as_json(path, xref, {"/A": 1, "/B": None})

        assert low_level_read_object_value(path, xref, "A") == ("int", "1")
        assert low_level_read_object_value(path, xref, "B")[0] == "null"

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_write_object_as_json(str(tmp_path / "missing.pdf"), 1, {})


class TestLowLevelCreateIndirectObject:
    def test_creates_new_object_with_new_xref(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        a = new_xref(path, "<< /A 1 >>")
        b = new_xref(path, "<< /B 2 >>")

        assert a != b
        assert low_level_read_object_value(path, a, "A") == ("int", "1")
        assert low_level_read_object_value(path, b, "B") == ("int", "2")

    def test_default_is_empty_dictionary(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path)

        assert low_level_read_object(path, xref).replace(" ", "").replace("\n", "") == "<<>>"

    def test_with_stream(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")
        xref = new_xref(path, "<<>>", b"abc")

        assert low_level_read_stream(path, xref) == b"abc"

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_create_indirect_object(str(tmp_path / "missing.pdf"))


class TestLowLevelCreateIndirectObjectAsJson:
    def test_creates_object_from_json(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")

        result = low_level_create_indirect_object_as_json(path, {"/A": 1, "/N": "/Nm"})
        xref = int(result.rsplit(" ", 1)[1])

        assert low_level_read_object_value(path, xref, "A") == ("int", "1")
        assert low_level_read_object_value(path, xref, "N") == ("name", "/Nm")

    def test_with_stream(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf")

        result = low_level_create_indirect_object_as_json(path, {"/A": 1}, b"abc")
        xref = int(result.rsplit(" ", 1)[1])

        assert low_level_read_stream(path, xref) == b"abc"

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            low_level_create_indirect_object_as_json(str(tmp_path / "missing.pdf"), {})


class TestJsonToPdf:
    @pytest.mark.parametrize("value,expected", [
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (5, "5"),
        (1.5, "1.5"),
        ("xref:12", "12 0 R"),
        ("b:DEADBEEF", "<DEADBEEF>"),
        ("/Name", "/Name"),
        ([1, "/A", None], "[1 /A null]"),
    ])
    def test_scalars_and_containers(self, value, expected):
        assert _json_to_pdf(value) == expected

    def test_unicode_string(self):
        assert _json_to_pdf("u:hello") == "(hello)"

    def test_dictionary(self):
        out = _json_to_pdf({"/A": 1, "/B": [2]})
        assert out.startswith("<<") and out.endswith(">>")
        assert "/A 1" in out and "/B [2]" in out

    def test_unconvertible_string_raises(self):
        with pytest.raises(ValueError):
            _json_to_pdf("nope")

    def test_binary_string_with_non_hex_raises(self):
        with pytest.raises(ValueError):
            _json_to_pdf("b:XYZ")


class TestJsonToPdfName:
    def test_valid_name_unchanged(self):
        assert _json_to_pdf_name("/Valid#20Name") == "/Valid#20Name"

    @pytest.mark.parametrize("name,expected", [
        ("/A(B", "/A#28B"),
        ("/A/B", "/A#2FB"),
        ("/A%B", "/A#25B"),
    ])
    def test_delimiter_is_escaped(self, name, expected):
        assert _json_to_pdf_name(name) == expected

    def test_invalid_name_fully_escapes_hash(self):
        assert _json_to_pdf_name("/A(#00") == "/A#28#23" + "00"

    def test_non_ascii_is_utf8_escaped(self):
        assert _json_to_pdf_name("/é(") == "/#C3#A9#28"

    def test_non_name_raises(self):
        with pytest.raises(ValueError):
            _json_to_pdf_name("NoSlash")
