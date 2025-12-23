from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_document(file_path) -> List[Document]:
    loader = PyPDFLoader(file_path)
    return loader.load()
