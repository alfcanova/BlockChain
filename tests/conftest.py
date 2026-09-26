"""Configuracao global dos testes.

Isola o banco de testes do banco de producao (database/blockchain.db):
define BLOCKCHAIN_DB ANTES de qualquer import de web_app/database,
aproveitando o override F3.2.
"""
import os
import shutil
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="blockchain_test_db_")
os.environ["BLOCKCHAIN_DB"] = os.path.join(_TMP_DIR, "test_blockchain.db")
# F2: rate limiter desligado na suíte (logins repetidos por teste;
# testes específicos de rate limit reativam via monkeypatch).
os.environ["RATE_LIMIT_ENABLED"] = "0"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    yield
    shutil.rmtree(_TMP_DIR, ignore_errors=True)