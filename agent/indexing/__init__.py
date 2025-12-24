import os
from pathlib import Path

from agent.vector_store import vector_store

from .load_document import load_document
from .text_splitter import split_documents

current_dir = Path(__file__).resolve().parent

file_path = os.path.join(current_dir, "work_code.pdf")


def index_documents():
    docs = load_document(file_path)
    all_splits = split_documents(docs)
    vector_store.add_documents(documents=all_splits)
