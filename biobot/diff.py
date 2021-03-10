#    Bio Bot (Telegram bot for managing the @Bio_Chain_2)
#    Copyright (C) 2019 Hackintosh Five

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import collections
from matplotlib import pyplot as plt
import networkx as nx
import io
import random
import math


def _default_namer(uid, username, full):
    if not username:
        return uid
    if full and uid:
        return f"{username} ({uid})"
    return username


def _linking_namer(uid, username, full):
    if not uid:
        return f"<a href=\"https://t.me/{username}\">{username}</a>"
    if full and username and uid:
        return f"<a href=\"https://t.me/{username}\">{username}</a> (<a href=\"tg://user?id={uid}\">{uid}</a>)"
    return f"<a href=\"tg://user?id={uid}\">{username or uid}</a>"


def _graph_to_dict(data):
    ret = {}
    for name, children in data.adjacency():
        node = data.nodes[name]
        uid = node["uid"]
        username = node["username"]
        ret[(uid, username.casefold() if username else username)] = [child.casefold() for child in children]
    return ret


def _generate_diff_data(old_data, new_data, namer):
    old_data = _graph_to_dict(old_data)
    new_data = _graph_to_dict(new_data)

    old_uid_to_username = {uid: username for uid, username in old_data.keys() if uid is not None and username is not None}
    new_uid_to_username = {uid: username for uid, username in new_data.keys() if uid is not None and username is not None}
    old_username_to_uid = {username: uid for uid, username in old_data.keys() if uid is not None and username is not None}

    duplicate_uids = set()
    duplicate_usernames = set()
    for uid, username in new_data.keys():
        if uid is not None and old_uid_to_username.get(uid, False) not in (username, False):
            duplicate_uids.add(uid)
        if username is not None and old_username_to_uid.get(username, False) not in (uid, False):
            duplicate_usernames.add(username)

    old_names = {username or uid: namer(uid, username, uid in duplicate_uids or username in duplicate_usernames) for uid, username in old_data}
    new_names = {username or uid: namer(uid, username, uid in duplicate_uids or username in duplicate_usernames) for uid, username in new_data}

    old_edges = {(old_names[username or uid], old_names.setdefault(child, child)) for (uid, username), children in old_data.items() for child in children}
    new_edges = {(new_names[username or uid], new_names.setdefault(child, child)) for (uid, username), children in new_data.items() for child in children}
    common_edges = old_edges & new_edges
    old_only_edges = old_edges - new_edges
    new_only_edges = new_edges - old_edges

    old_names_set = set(old_names.values())
    new_names_set = set(new_names.values())
    all_names = old_names_set | new_names_set
    common_names = old_names_set | new_names_set
    old_only_names = old_names_set - new_names_set
    new_only_names = new_names_set - old_names_set

    uid_edges = set()
    username_edges = set()

    for uid in duplicate_uids:
        old_name = old_names[old_uid_to_username.get(uid, uid)]
        new_name = new_names[new_uid_to_username.get(uid, uid)]
        uid_edges.add((old_name, new_name))
#        common_names.add(old_name)
#        common_names.add(new_name)
#        old_only_names.discard(old_name)
#        new_only_names.discard(new_name)

    for username in duplicate_usernames:
        old_name = old_names[username]
        new_name = new_names[username]
        username_edges.add((old_name, new_name))
#        common_names.add(old_name)
#        common_names.add(new_name)
#        old_only_names.discard(old_name)
#        new_only_names.discard(new_name)

    return common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names


def _generate_diff_graph(old_data, new_data, namer):
    common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names = _generate_diff_data(old_data, new_data, namer)
    graph = nx.DiGraph()
    for src, dest in common_edges:
        graph.add_edge(src, dest, type="common", weight=0.5)
    for src, dest in old_only_edges:
        graph.add_edge(src, dest, type="old", weight=0.5)
    for src, dest in new_only_edges:
        graph.add_edge(src, dest, type="new", weight=0.5)
    for src, dest in uid_edges:
        graph.add_edge(src, dest, type="uid", weight=1)
    for src, dest in username_edges:
        graph.add_edge(src, dest, type="username", weight=1)

    for name in common_names:
        graph.add_node(name, type="common")
    for name in old_only_names:
        graph.add_node(name, type="old")
    for name in new_only_names:
        graph.add_node(name, type="new")

    return graph, common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names


def textual_chain_diff(old_data, new_data, directed_delim, line_delim):
    _, old_only_edges, new_only_edges, uid_edges, username_edges, _, old_only_names, new_only_names = _generate_diff_data(old_data, new_data, _linking_namer)
    old_only_edges = line_delim.join(directed_delim.join(edge) for edge in old_only_edges)
    new_only_edges = line_delim.join(directed_delim.join(edge) for edge in new_only_edges)
    uid_edges = line_delim.join(directed_delim.join(edge) for edge in uid_edges)
    username_edges = line_delim.join(directed_delim.join(edge) for edge in username_edges)
    old_only_names = line_delim.join(old_only_names)
    new_only_names = line_delim.join(new_only_names)
    return old_only_edges, new_only_edges, uid_edges, username_edges, old_only_names, new_only_names


def draw_chain_diff(old_data, new_data):
    graph, common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names = _generate_diff_graph(old_data, new_data, _default_namer)

    fig = plt.figure(figsize=(200, 124))
    ax = plt.axes()
    pos = {}
    # initialize each component at a different random location
    components = set(frozenset(c) for c in nx.weakly_connected_components(graph))
    dist = dict(nx.shortest_path_length(graph))
    for sources in components:
        for dests in components:
            if sources is dests:
                continue
            for source in sources:
                for dest in dests:
                    dist[source][dest] = 10 + len(sources) / 10 + len(dests) / 10
    for component in nx.weakly_connected_components(graph):
        x = random.triangular()
        y = random.triangular()
        for node in component:
            pos[node] = ((x * 4 + random.triangular()) / 5, (y * 4 + random.triangular()) / 5)
    pos = nx.kamada_kawai_layout(graph, dist=dist)
    pos = nx.rescale_layout_dict(pos, 50)
    nx.draw_networkx_nodes(graph, pos, ax=ax, nodelist=common_names, node_color="tab:blue", node_size=20)
    nx.draw_networkx_nodes(graph, pos, ax=ax, nodelist=old_only_names, node_color="tab:red", node_size=20)
    nx.draw_networkx_nodes(graph, pos, ax=ax, nodelist=new_only_names, node_color="tab:green", node_size=20)
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=common_edges, width=2, alpha=0.5, edge_color="tab:blue")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=new_only_edges, width=2, alpha=0.5, edge_color="tab:green")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=old_only_edges, width=2, alpha=0.5, edge_color="tab:red")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=uid_edges, width=2, alpha=0.5, edge_color="tab:orange")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=username_edges, width=2, alpha=0.5, edge_color="tab:pink")
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=5)
    data = io.BytesIO()
    data.name = "chain.svg"
    fig.savefig(data, dpi=120, bbox_inches="tight", format="svg")
    data.seek(0)
    return data
