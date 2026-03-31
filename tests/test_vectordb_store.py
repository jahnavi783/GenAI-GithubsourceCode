from vectordb import store


class FakeCollection:
    def __init__(self):
        self.calls = []
        self.data = {}

    def upsert(self, documents, metadatas, ids):
        self.calls.append((documents, metadatas, ids))
        self.data[ids[0]] = {"document": documents[0], "metadata": metadatas[0]}

    def get(self, ids, include=None):
        _ = include
        found = [item_id for item_id in ids if item_id in self.data]
        return {"ids": found}

    def query(self, query_texts, n_results):
        _ = query_texts
        _ = n_results
        if not self.data:
            return {"metadatas": [[]]}
        first = next(iter(self.data.values()))
        return {"metadatas": [[first["metadata"]]]}


def test_store_commit_is_idempotent(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(store, "collection", fake)

    store.store_commit("abc", "diff1", "doc1", "author")
    store.store_commit("abc", "diff2", "doc2", "author")

    assert len(fake.calls) == 2
    assert store.commit_exists("abc") is True
    assert fake.data["abc"]["document"] == "diff2"


def test_retrieve_similar_returns_documentation(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(store, "collection", fake)
    fake.upsert(["diff"], [{"documentation": "doc text"}], ["id1"])

    results = store.retrieve_similar("query", top_k=3)

    assert results == [{"documentation": "doc text"}]
