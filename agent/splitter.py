import os

from dotenv import load_dotenv
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymongo import MongoClient

from .embeddings import embeddings
from .load_document import docs

load_dotenv()

client = MongoClient(os.environ["MONGODB_URI"])

DB_NAME = os.environ["MONGODB_DB"]
COLLECTION_NAME = os.environ["MONGODB_COLLECTION"]
ATLAS_VECTOR_SEARCH_INDEX_NAME = os.environ["MONGODB_INDEX"]

MONGODB_COLLECTION = client[DB_NAME][COLLECTION_NAME]

vector_store = MongoDBAtlasVectorSearch(
    embedding=embeddings,
    collection=MONGODB_COLLECTION,
    index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
    relevance_score_fn="cosine",
)


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # chunk size (characters)
    chunk_overlap=200,  # chunk overlap (characters)
    add_start_index=True,  # track index in original document
)

all_splits = text_splitter.split_documents(docs)

document_ids = vector_store.add_documents(documents=all_splits)
