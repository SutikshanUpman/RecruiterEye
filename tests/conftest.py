"""Tests never load local secrets or call external services."""
import sys
import socket
from types import ModuleType

import pytest

config = ModuleType("backend.core.config")
config.GITHUB_TOKEN = "test-github-token"
config.GROQ_API_KEY = "test-groq-key"
sys.modules["backend.core.config"] = config


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def guard(original):
        def connect(sock, address):
            # Windows asyncio uses loopback sockets for its internal wakeup pipe.
            if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
                return original(sock, address)
            raise AssertionError("Tests must mock external service calls")
        return connect

    monkeypatch.setattr(socket.socket, "connect", guard(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guard(socket.socket.connect_ex))
