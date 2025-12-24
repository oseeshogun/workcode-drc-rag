from agent import agent

query = "Explique-moi l'article 41 s'il te plaît?"

for event in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()
