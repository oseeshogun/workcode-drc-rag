from langchain.agents import create_agent

from .model import model
from .retrieve_context import retrieve_context

tools = [retrieve_context]
# If desired, specify custom instructions
prompt = (
    "Tu es un assistant qui répond aux questions sur le travail. "
    "Utilise les outils pour aider à répondre aux questions des utilisateurs."
    "Tu maîtrises le code du travail de la RDC."
    "Fournis les articles pour appuyer ta réponse."
)
agent = create_agent(model, tools, system_prompt=prompt)
