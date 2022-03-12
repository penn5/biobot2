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


from matplotlib import pyplot as plt
import networkx as nx
import numpy as np
import io
import random
from .chain import make_chain


def _default_namer(uid, username, full, node):
    if not username:
        ret = str(uid)
    elif full and uid:
        ret = f"{username} ({uid})"
    else:
        ret = username
    if node.get("deleted", False):
        ret += "⌫"
    return ret


def _linking_namer(uid, username, full, node):
    if not uid:
        ret = f"<a href=\"https://t.me/{username}\">{username}</a>"
    elif full and username and uid:
        ret = f"<a href=\"https://t.me/{username}\">{username}</a> (<a href=\"tg://user?id={uid}\">{uid}</a>)"
    else:
        ret = f"<a href=\"tg://user?id={uid}\">{username or uid}</a>"
    if node.get("deleted", False):
        ret += "⌫"
    return ret


def _graph_to_dict(data):
    ret = {}
    names = {}
    for name, children in data.adjacency():
        node = data.nodes[name]
        uid = node["uid"]
        username = node["username"] and node["username"].casefold()
        ret[(uid, username)] = [child.casefold() for child in children if child != username]
        names[(uid, username)] = name
    return ret, names


def _generate_diff_data(old_graph, new_graph, namer, ignore_edits):
    old_data, old_map = _graph_to_dict(old_graph)
    new_data, new_map = _graph_to_dict(new_graph)

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

    old_names = {username or uid: namer(uid, username, uid in duplicate_uids or username in duplicate_usernames, old_graph.nodes[old_map[(uid, username)]]) for uid, username in old_data}
    new_names = {username or uid: namer(uid, username, uid in duplicate_uids or username in duplicate_usernames, new_graph.nodes[new_map[(uid, username)]]) for uid, username in new_data}

    old_edges = {(old_names[username or uid], old_names.setdefault(child, child)) for (uid, username), children in old_data.items() for child in children}
    new_edges = {(new_names[username or uid], new_names.setdefault(child, child)) for (uid, username), children in new_data.items() for child in children}
    common_edges = old_edges & new_edges
    old_only_edges = old_edges - new_edges
    new_only_edges = new_edges - old_edges

    old_names_set = set(old_names.values())
    new_names_set = set(new_names.values())
    common_names = old_names_set | new_names_set
    old_only_names = old_names_set - new_names_set
    new_only_names = new_names_set - old_names_set

    uid_edges = set()
    username_edges = set()

    for uid in duplicate_uids:
        old_name = old_names[old_uid_to_username.get(uid, uid)]
        new_name = new_names[new_uid_to_username.get(uid, uid)]
        uid_edges.add((old_name, new_name))
        if ignore_edits:
            common_names.add(old_name)
            common_names.add(new_name)
            old_only_names.discard(old_name)
            new_only_names.discard(new_name)

    for username in duplicate_usernames:
        old_name = old_names[username]
        new_name = new_names[username]
        username_edges.add((old_name, new_name))
        if ignore_edits:
            common_names.add(old_name)
            common_names.add(new_name)
            old_only_names.discard(old_name)
            new_only_names.discard(new_name)

    return common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names, old_names, new_names


def _generate_diff_graph(old_data, new_data, namer, ignore_edits):
    common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names, old_names, new_names = _generate_diff_data(old_data, new_data, namer, ignore_edits)
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

    return graph, common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names, old_names, new_names


def textual_chain_diff(old_data, new_data, directed_delim, line_delim):
    _, old_only_edges, new_only_edges, uid_edges, username_edges, _, old_only_names, new_only_names, _, _ = _generate_diff_data(old_data, new_data, _linking_namer, True)
    old_only_edges = line_delim.join(directed_delim.join(edge) for edge in old_only_edges)
    new_only_edges = line_delim.join(directed_delim.join(edge) for edge in new_only_edges)
    uid_edges = line_delim.join(directed_delim.join(edge) for edge in uid_edges)
    username_edges = line_delim.join(directed_delim.join(edge) for edge in username_edges)
    old_only_names = line_delim.join(old_only_names)
    new_only_names = line_delim.join(new_only_names)
    return old_only_edges, new_only_edges, uid_edges, username_edges, old_only_names, new_only_names


def draw_chain_diff(old_data, new_data, target, format, extension=None):
    graph, common_edges, old_only_edges, new_only_edges, uid_edges, username_edges, common_names, old_only_names, new_only_names, old_names, new_names = _generate_diff_graph(old_data, new_data, _default_namer, False)

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
    # prevent duplicate distances
    last_dist = -1
    last_keys = []
    for source, dists in dist.items():
        for dest, distance in sorted(dists.items(), key=lambda k: (k[1], str(k[0]))):
            if distance != last_dist:
                count = len(last_keys)
                interval = 2 / (count + 1)
                for i, key in enumerate(last_keys):
                    dists[key] = (i + 1) * interval + last_dist - 1
                last_keys.clear()
                last_dist = distance
            last_keys.append(dest)
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
    if target:
        old_chain = [old_names[username] for username in make_chain(old_data, target)]
        old_chain = [(old_chain[i], old_chain[i + 1]) for i in range(len(old_chain) - 1)]
        new_chain = [new_names[username] for username in make_chain(new_data, target)]
        new_chain = [(new_chain[i], new_chain[i + 1]) for i in range(len(new_chain) - 1)]
        nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=new_chain, width=6, alpha=0.1, edge_color=np.linspace(0, 1, len(new_chain)), edge_cmap=plt.get_cmap("cool"))
        nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=old_chain, width=6, alpha=0.1, edge_color=np.linspace(0, 1, len(old_chain)), edge_cmap=plt.get_cmap("autumn"))
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=common_edges, width=2, alpha=0.5, edge_color="tab:blue")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=new_only_edges, width=2, alpha=0.5, edge_color="tab:green")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=old_only_edges, width=2, alpha=0.5, edge_color="tab:red")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=uid_edges, width=2, alpha=0.5, edge_color="tab:orange")
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=username_edges, width=2, alpha=0.5, edge_color="tab:pink")
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=5)
    data = io.BytesIO()
    data.name = "chain." + (extension or format)
    fig.savefig(data, dpi=120, bbox_inches="tight", format=format)
    data.seek(0)
    return data
