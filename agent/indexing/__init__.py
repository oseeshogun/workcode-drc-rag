from agent.vector_store import vector_store

from .load_document import load_document
from .text_splitter import split_documents

file_path = (
    "https://legalrdc.com/wp-content/uploads/2019/12/Code_du_travail_LegalRDC-1.pdf"
)


def index_documents():
    docs = load_document(file_path)
    all_splits = split_documents(docs)
    vector_store.add_documents(documents=all_splits)
