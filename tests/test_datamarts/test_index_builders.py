import json

import pytest

from src.datamarts.inverted_index import build_folder_index, build_inverted_index, build_mongo_index
from src.datamarts.inverted_index.corpus import load_corpus
from src.datamarts.inverted_index.folder_index import load_index as load_folder_index
from src.datamarts.inverted_index.mongo_index import is_available
from src.datamarts.metadata.book_processor import process_datalake


@pytest.fixture
def indexed_storage(datalake_dir, metadata_storage):
    process_datalake(metadata_storage, datalake_dir)
    return metadata_storage


def use_storage(monkeypatch, builder_module, storage):
    monkeypatch.setattr(builder_module, "SQLiteStorage", lambda: storage)


class TestLoadCorpus:
    def test_reads_bodies_through_metadata_paths(self, indexed_storage):
        books = load_corpus(indexed_storage)
        assert sorted(books) == [11, 84, 1342]
        assert "darcy" in books[1342]
        assert "the" not in books[1342]

    def test_empty_metadata_store_warns(self, metadata_storage, caplog):
        assert load_corpus(metadata_storage) == {}
        assert "book_processor" in caplog.text


class TestBuilderScripts:
    def test_json_builder_indexes_the_datalake(self, indexed_storage, tmp_path, monkeypatch):
        use_storage(monkeypatch, build_inverted_index, indexed_storage)
        monkeypatch.setattr(build_inverted_index, "JSON_INDEX_PATH", tmp_path / "out" / "inverted_index.json")
        build_inverted_index.main()
        index = json.loads((tmp_path / "out" / "inverted_index.json").read_text(encoding="utf-8"))
        assert index["rabbit"] == [11, 1342]
        assert len(index) < 20, "only the three tiny datalake books must be indexed, not sample_data"

    def test_folder_builder_indexes_the_datalake(self, indexed_storage, tmp_path, monkeypatch):
        use_storage(monkeypatch, build_folder_index, indexed_storage)
        monkeypatch.setattr(build_folder_index, "FOLDER_INDEX_DIR", tmp_path / "folder_index")
        build_folder_index.main()
        index = load_folder_index(tmp_path / "folder_index")
        assert index["rabbit"] == [11, 1342]
        assert index["creature"] == [84]

    @pytest.mark.skipif(not is_available(), reason="MongoDB is not available at mongodb://localhost:27017")
    def test_mongo_builder_indexes_the_datalake(self, indexed_storage, monkeypatch):
        from src.datamarts.inverted_index.mongo_index import get_collection, query_index

        collection = get_collection(database_name="search_engine_builder_test")
        use_storage(monkeypatch, build_mongo_index, indexed_storage)
        monkeypatch.setattr(build_mongo_index, "get_collection", lambda: collection)
        try:
            build_mongo_index.main()
            assert query_index("rabbit", collection) == [11, 1342]
        finally:
            collection.database.client.drop_database("search_engine_builder_test")
