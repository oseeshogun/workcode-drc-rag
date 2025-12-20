from agent import agent

query = "Que dit l'article 41 du code du travail ?"

for event in agent.stream(
    {"messages": [{"role": "user", "content": query}]},
    stream_mode="values",
):
    event["messages"][-1].pretty_print()
