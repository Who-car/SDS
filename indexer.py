import os
import json
from pathlib import Path

import faiss
import numpy as np
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings


class Indexer:
    def __init__(
        self,
        catalog_path: str = 'metadata/catalog.json',
        catalog_index_dir: str = 'faiss_index_catalog',
        product_path: str = 'data_preprocessed',
        product_index_dir: str = 'faiss_index_products',
        embedding_model: str = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
    ):
        self.catalog_path = Path(catalog_path)
        self.catalog_index_dir = Path(catalog_index_dir)
        self.product_path = Path(product_path)
        self.product_index_dir = Path(product_index_dir)
        self.embedding_model = embedding_model
        self.catalog_docs = []
        self.product_docs = []
        self.embedding = HuggingFaceEmbeddings(model_name=embedding_model)
        self.catalog_index = None
        self.product_index = None
        self.catalog_embeddings_file = self.catalog_index_dir / 'embeddings.npy'
        self.product_embeddings_file = self.product_index_dir / 'embeddings.npy'
        self.catalog_index_file = self.catalog_index_dir / 'index.faiss'
        self.product_index_file = self.product_index_dir / 'index.faiss'
        self._load_data()
        self._ensure_index()

    def _load_data(self) -> None:
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        self.catalog_docs = [Document(page_content=item, metadata={'name': item}) for item in items]

        products_data = []
        product_docs = []
        for filename in os.listdir(self.product_path):
            if not filename.lower().endswith('.json') or filename.lower().startswith('stats'):
                continue
            path = os.path.join(self.product_path, filename)
            with open(path, "r", encoding="utf-8") as f:
                products_data.extend(json.load(f))
        for prod in products_data:
            title = prod.get("name", "").strip()
            desc = prod.get("description", "").strip()
            text = f"{title}\n\n{desc}"
            product_docs.append(Document(
                page_content=text,
                metadata={
                    "name": title,
                    "description": desc,
                    "productid": prod["productid"],
                    "article": prod["article"],
                    "brand": prod["brand"],
                    "country": prod["country"],
                    "etimclass": prod.get("etimclass")
                }
            ))
        self.product_docs = product_docs

    def _ensure_index(self) -> None:
        self.catalog_index_dir.mkdir(parents=True, exist_ok=True)
        if self.catalog_embeddings_file.exists() and self.catalog_index_file.exists():
            matrix = np.load(self.catalog_embeddings_file)
            self.catalog_index = faiss.read_index(str(self.catalog_index_file))
        else:
            matrix = self._compute_embeddings(self.catalog_docs)
            np.save(self.catalog_embeddings_file, matrix)
            self.catalog_index = faiss.IndexFlatIP(matrix.shape[1])
            self.catalog_index.add(matrix)
            faiss.write_index(self.catalog_index, str(self.catalog_index_file))

        self.product_index_dir.mkdir(parents=True, exist_ok=True)
        if self.product_embeddings_file.exists() and self.product_index_file.exists():
            matrix = np.load(self.product_embeddings_file)
            self.product_index = faiss.read_index(str(self.catalog_index_file))
        else:
            matrix = self._compute_embeddings(self.product_docs)
            np.save(self.product_embeddings_file, matrix)
            self.product_index = faiss.IndexFlatIP(matrix.shape[1])
            self.product_index.add(matrix)
            faiss.write_index(self.product_index, str(self.product_index_file))

    def _compute_embeddings(self, docs: list[Document]) -> np.ndarray:
        vectors = []
        for doc in docs:
            vec = np.array(self.embedding.embed_query(doc.page_content), dtype='float32')
            vec /= np.linalg.norm(vec)
            vectors.append(vec)
        return np.vstack(vectors)

    def search_catalog(self, query: str, threshold: float) -> list[Document]:
        q_vec = np.array(self.embedding.embed_query(query), dtype='float32')
        q_vec /= np.linalg.norm(q_vec)
        distances, indices = self.catalog_index.search(q_vec.reshape(1, -1), self.catalog_index.ntotal)
        results, top = [], None
        for score, idx in zip(distances[0], indices[0]):
            top = top or (self.catalog_docs[idx], score)
            if score < threshold:
                break
            results.append(self.catalog_docs[idx])
        if len(results) > 0: 
            return results
        elif threshold - top[1] <= 0.2: 
            return [top[0]]
        else: 
            return None
    
    def search_product(self, query: str, threshold: float = 0.95) -> list[Document]:
        q_vec = np.array(self.embedding.embed_query(query), dtype='float32')
        q_vec /= np.linalg.norm(q_vec)
        distances, indices = self.product_index.search(q_vec.reshape(1, -1), self.product_index.ntotal)
        results, top = [], None
        for score, idx in zip(distances[0], indices[0]):
            top = top or (self.product_docs[idx], score)
            if score < threshold:
                break
            results.append(self.product_docs[idx])
        return results or [top[0]]