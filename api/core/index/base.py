from __future__ import annotations
from abc import abstractmethod, ABC
from typing import List, Any

from langchain.schema import Document, BaseRetriever


class BaseIndex(ABC):
    @abstractmethod
    def create(self, texts: list[Document]) -> BaseIndex:
        raise NotImplementedError

    @abstractmethod
    def add_texts(self, texts: list[Document]):
        raise NotImplementedError

    @abstractmethod
    def text_exists(self, id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_by_ids(self, ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_by_document_id(self, document_id: str):
        raise NotImplementedError

    @abstractmethod
    def get_retriever(self, **kwargs: Any) -> BaseRetriever:
        raise NotImplementedError

    @abstractmethod
    def search(
            self, query: str,
            **kwargs: Any
    ) -> List[Document]:
        raise NotImplementedError

    def _filter_duplicate_texts(self, texts: list[Document]) -> list[Document]:
        for text in texts:
            doc_id = text.metadata['doc_id']
            exists_duplicate_node = self.text_exists(doc_id)
            if exists_duplicate_node:
                texts.remove(text)

        return texts

    def _get_uuids(self, texts: list[Document]) -> list[str]:
        return [text.metadata['doc_id'] for text in texts]
