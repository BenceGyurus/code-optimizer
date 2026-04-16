from optimizer.retrieval.store import RetrievalStore


def query(store: RetrievalStore, text: str, limit: int = 3):
    return store.query(text, limit=limit)
