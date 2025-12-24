from langchain.agents.middleware.types import ModelRequest, dynamic_prompt
from langchain.tools import tool

from agent.vector_store import vector_store


@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve information to help answer a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    print(retrieved_docs)
    return serialized, retrieved_docs
