"""Importing a benchmark module must leave the logging configuration to the caller."""

import importlib
import logging
import sys

import pytest

BENCHMARK_MODULES = [
    "src.utils.benchmarks.benchmark_implementations",
    "src.utils.benchmarks.datalake_experiments",
    "src.utils.benchmarks.inverted_index_experiments",
    "src.utils.benchmarks.metadata_experiments",
    "src.utils.benchmarks.setup_environment",
]


@pytest.mark.parametrize("module_name", BENCHMARK_MODULES)
def test_import_does_not_configure_the_root_logger(module_name, monkeypatch):
    root_logger = logging.getLogger()
    monkeypatch.setattr(root_logger, "handlers", [])
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    importlib.import_module(module_name)
    assert root_logger.handlers == []
