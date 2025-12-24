from langchain.agents import create_agent

from agent.agent_tools.retrieve_context import retrieve_context
from agent.agent_tools.work_code_functools import (
    get_article_by_number,
    get_work_code_structure,
)

from .model import model

tools = [retrieve_context, get_work_code_structure, get_article_by_number]


# If desired, specify custom instructions
prompt = (
    "Tu es un assistant qui répond aux questions sur le travail. "
    "Utilise les outils pour aider à répondre aux questions des utilisateurs. "
    "Tu maîtrises le code du travail de la RDC. "
    "Fournis les articles pour appuyer ta réponse."
)

agent = create_agent(model, tools, system_prompt=prompt)
