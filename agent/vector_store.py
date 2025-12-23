import os

from dotenv import load_dotenv
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient

from .embeddings import embeddings

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
