import collections
from matplotlib import pyplot as plt
import networkx as nx
import io


def draw_chain_diff(old_data, new_data):
    old_data = {(uid, username.casefold()): [child.casefold() for child in children] for (uid, username), children in old_data.items()}
    new_data = {(uid, username.casefold()): [child.casefold() for child in children] for (uid, username), children in new_data.items()}
    old_uid_to_username = dict(old_data.keys())
    new_uid_to_username = dict(new_data.keys())
    old_username_to_uid = {username: uid for uid, username in old_data.keys() if uid is not None}
    duplicate_uids = set()
    duplicate_usernames = set()
    for uid, username in new_data.keys():
        if uid is not None and old_uid_to_username.get(uid, False) not in (username, False):
            duplicate_uids.add(uid)
        if old_username_to_uid.get(username, False) not in (uid, False):
            duplicate_usernames.add(username)
    old_names = {username: (f"{username} ({uid})" if uid in duplicate_uids or username in duplicate_usernames else username) for (uid, username) in old_data.keys()}
    new_names = {username: (f"{username} ({uid})" if uid in duplicate_uids or username in duplicate_usernames else username) for (uid, username) in new_data.keys()}
    all_names = list(old_names.values()) + list(new_names.values())
    old_edges = {(old_names[username], old_names[child]) for (_, username), children in old_data.items() for child in children}
    new_edges = {(new_names[username], new_names[child]) for (_, username), children in new_data.items() for child in children}
    common_edges = old_edges & new_edges
    old_only_edges = old_edges - new_edges
    new_only_edges = new_edges - old_edges
    uid_edges = set()
    username_edges = set()
    edges = collections.defaultdict(dict)
    for src, dest in common_edges:
        edges[src][dest] = {"type": "common", "weight": 0.5}
    for src, dest in old_only_edges:
        edges[src][dest] = {"type": "old", "weight": 0.5}
    for src, dest in new_only_edges:
        edges[src][dest] = {"type": "new", "weight": 0.5}
    for uid in duplicate_uids:
        old_name = old_names[old_uid_to_username[uid]]
        new_name = new_names[new_uid_to_username[uid]]
        uid_edges.add((old_name, new_name))
        uid_edges.add((new_name, old_name))
    for src, dest in uid_edges:
        edges[src][dest] = {"type": "uid", "weight": 1}
    for username in duplicate_usernames:
        old_name = old_names[username]
        new_name = new_names[username]
        username_edges.add((old_name, new_name))
        username_edges.add((new_name, old_name))
    for src, dest in username_edges:
        edges[src][dest] = {"type": "username", "weight": 1}
    graph = nx.DiGraph(edges)
    fig = plt.figure(figsize=(200, 124))
    ax = plt.axes()
    pos = nx.spring_layout(graph)
    pos = nx.kamada_kawai_layout(graph, pos=pos)
    pos = nx.rescale_layout_dict(pos, 50)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color="tab:blue", node_size=20)
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=common_edges, width=2, alpha=0.5, edge_color="tab:blue")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=new_only_edges, width=2, alpha=0.5, edge_color="tab:green")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=old_only_edges, width=2, alpha=0.5, edge_color="tab:red")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=uid_edges, width=2, alpha=0.5, edge_color="tab:orange")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=username_edges, width=2, alpha=0.5, edge_color="tab:pink")
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=5)
    data = io.BytesIO()
    data.name = "chain.svg"
    fig.savefig(data, dpi=500, bbox_inches="tight", format="svg")
    data.seek(0)
    return data
