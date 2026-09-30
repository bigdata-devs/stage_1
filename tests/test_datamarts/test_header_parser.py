from src.datamarts.metadata.header_parser import extract_metadata, normalize_language, parse_header_fields

GUTENBERG_HEADER = """The Project Gutenberg eBook of Pride and Prejudice\r\r
    \r\r
This eBook is for the use of anyone anywhere in the United States and\r\r
at www.gutenberg.org. If you are not located in the United States,\r\r
\r\r
Title: The Works of Edgar Allan Poe\r\r
       Volume 1\r\r
\r\r
Author: Edgar Allan Poe\r\r
\r\r
Editor: Someone Else\r\r
\r\r
Release date: April 1, 2000 [eBook #2147]\r\r
                Most recently updated: May 5, 2021\r\r
\r\r
Language: English\r\r
"""


class TestParseHeaderFields:
    def test_joins_indented_continuation_lines(self):
        fields = parse_header_fields(GUTENBERG_HEADER)
        assert fields["title"] == ["The Works of Edgar Allan Poe Volume 1"]
        assert fields["release date"] == ["April 1, 2000 [eBook #2147] Most recently updated: May 5, 2021"]

    def test_ignores_preamble_sentences(self):
        fields = parse_header_fields(GUTENBERG_HEADER)
        assert set(fields) == {"title", "author", "editor", "release date", "language"}

    def test_keeps_repeated_fields(self):
        fields = parse_header_fields("Author: First Person\nAuthor: Second Person\n")
        assert fields["author"] == ["First Person", "Second Person"]


class TestExtractMetadata:
    def test_extracts_normalized_fields(self):
        assert extract_metadata(GUTENBERG_HEADER) == {
            "title": "The Works of Edgar Allan Poe Volume 1",
            "author": "Edgar Allan Poe",
            "language": "en",
        }

    def test_joins_several_authors(self):
        header = "Title: Joint Work\nAuthor: First Person\nAuthor: Second Person\nLanguage: French\n"
        assert extract_metadata(header)["author"] == "First Person; Second Person"

    def test_missing_fields_are_unknown(self):
        assert extract_metadata("Other: A Committee\n") == {"title": "Unknown", "author": "Unknown", "language": "Unknown"}


class TestNormalizeLanguage:
    def test_maps_names_to_codes(self):
        assert normalize_language("English") == "en"
        assert normalize_language("  german ") == "de"

    def test_maps_several_languages(self):
        assert normalize_language("English, French and Spanish") == "en,fr,es"

    def test_keeps_names_containing_commas(self):
        assert normalize_language("Greek, Ancient (to 1453)") == "grc"

    def test_keeps_unknown_languages_in_lower_case(self):
        assert normalize_language("Klingon") == "klingon"

    def test_empty_value_is_unknown(self):
        assert normalize_language("") == "Unknown"
