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

import ast
import collections
import io
import networkx
import pickle


"""Converts the username:bio dict to a tree of users, and optionally a list"""


class Forest:
    def __init__(self):
        self._instances = {}

    def get_roots(self):
        return filter(lambda x: not x.parents, self._instances.values())

    def get_nodes(self):
        return self._instances.values()

    def get_node(self, username, uid=None, add=True):
        try:
            ret = self._instances[username.lower()]
            assert uid is None or ret.uid == uid or ret.uid is None
            if uid is not None:
                ret.uid = uid
            return ret
        except KeyError:
            if not add:
                raise
            self._instances[username.lower()] = ret = User(self, username)
            ret.uid = uid
            return ret

    def get_dict(self):
        ret = {}
        for node in self.get_nodes():
            ret[(node.uid, node.username)] = [child.username for child in node.children]
        return ret

    def __getstate__(self):
        return {k: (v.username, v.uid, [child.username for child in v.children], v.extras)
                for k, v in self._instances.items()}

    def __setstate__(self, state):
        self._instances = {}
        for k, v in state.items():
            user = self._instances[k] = User(self, v[0])
            user.uid = v[1]
            user.extras = v[3]
        for k, v in state.items():
            for child_username in v[2]:
                self._instances[k].add_child(child_username)


class User:
    def __init__(self, forest, username):
        self.forest = forest
        self.username = username
        self.uid = None  # Not used in the actual tree, just used to simplify other code by preserving data
        self.extras = {}
        self.children = []
        self.parents = []

    def add_child(self, child_username):
        new = self.forest.get_node(child_username)
        new.parents.append(self)
        self.children.append(new)
        return new

    def _repr(self, instances):
        if self not in instances:
            return "{" + self.username + ": [" + ", ".join(child._repr(instances + [self])
                                                           for child in self.children) + "]}"
        else:
            return f"(recursive loop to {self.username})"

    def __str__(self):
        return self._repr([])

    def __repr__(self):
        return "User(username=" + repr(self.username) + ", uid=" + repr(self.uid) + ")"


def _destringize(data):
    if data == "_biobot_empty_list":
        return []
    try:
        return ast.literal_eval(data)
    except SyntaxError as e:
        raise ValueError from e


def make_graph(data, users_data={}):
    if isinstance(data, tuple):
        data, name = data
        if name == "raw_chain.forest":
            data = pickle.loads(data)
        elif name == "chain.gml":
            data = networkx.read_gml(io.BytesIO(data), destringizer=_destringize)
        else:
            raise RuntimeError(f"file name {name} incorrect")
    if isinstance(data, networkx.DiGraph):
        for node in data:
            if "username" in data.nodes[node]:
                data.nodes[node]["usernames"] = [data.nodes[node]["username"]]
        return data
    graph = networkx.DiGraph()
    if isinstance(data, Forest):
        old_data = data
        data = data.get_dict()
    else:
        old_data = None
    if isinstance(data, dict):
        for uid, username in data:
            graph.add_node(username.casefold() if username else uid, usernames=[username], uid=uid, deleted=None, about=None)
        for (uid, username), children in data.items():
            name = username.casefold() if username else uid
            for child in children:
                child_name = child.casefold()
                if child_name not in graph:
                    graph.add_node(child_name, usernames=[child], uid=None, deleted=None, about=None)
                graph.add_edge(name, child_name)
    else:  # list of FullUser
        username_to_key = {}
        for entry in data:
            graph.add_node(entry.key, usernames=entry.usernames, uid=entry.id, deleted=entry.deleted, about=entry.about)
            for username in entry.usernames:
                username_to_key[username.casefold()] = entry.key
        for entry in data:
            for child in entry.points_to:
                child_key = username_to_key.get(child.casefold(), None)
                if not child_key:
                    child_key = child.casefold()
                    graph.add_node(child_key, usernames=[child], uid=None, deleted=None, about=None)
                graph.add_edge(entry.key, child_key)
    if old_data:
        for node in old_data.get_nodes():
            name = node.username.casefold() if node.username else node.uid
            graph.nodes[name]["deleted"] = None
    return graph


def _score_node(val):
    name, score = val
    if isinstance(name, int):
        return score - 1
    return score


def _score_chain(chain):
    ret = len(chain)
    if isinstance(chain[0], int) or isinstance(chain[-1], int):
        ret -= 1
    return ret


def _edge_bfs(graph, root, get_children):
    # root is returned last
    queue = collections.deque(((None, root),))
    if root not in graph:
        return [root]
    visited_nodes = set()
    nexts = {(None, root): None}
    in_scores = {root: 0}
    out_scores = {root: 0}
    while queue:
        last_edge = queue.popleft()
        last_node, node = last_edge
        visited_nodes.add(node)
        children = tuple(get_children(graph, node))
        nexts[(node, None)] = last_edge
        for child in children:
            edge = (node, child)
            duplicate_node = False
            # quick and greedy heuristic to detect potential cycles
            if child in visited_nodes:
                # (slowly) verify cycle exists with latest iteration of the history (if this becomes outdated, a parent will always be added to queue and we will rerun this)
                next = last_edge
                duplicate_edge = False
                while next[0]:
                    if next == edge:
                        # the edge appears in our history, we already did this cycle
                        duplicate_edge = True
                        break
                    if next[1] == child:
                        duplicate_node = True
                    next = nexts[next]
                if duplicate_edge:
                    continue
            if out_scores[node] + 1 > in_scores.get(child, float("-inf")):
                queue.append(edge)
                out_scores[child] = out_scores[node] + 1
                if not duplicate_node:
                    # when a node is duplicated, we want to allow longer paths that go into it to replace the root, but we still want to count the loop towards the path score
                    in_scores[child] = out_scores[node] + 1
                nexts[edge] = last_edge
    best = max(out_scores.items(), key=_score_node)
    next = best[0], None
    ret = []
    while next[0]:
        ret.append(next[0])
        next = nexts[next]
    return ret


def make_chain(graph, target):
    # select longest path, preferring chains ending in a username
    return _edge_bfs(graph, target, networkx.DiGraph.predecessors)


def make_notinchain(graph, target):
    chain = make_chain(graph, target)
    return set(graph.nodes) - set(chain)


def make_all_chains(data):
    """
    Get a list of chains possible to generate from the data
    Prefers to make longer chains than shorter ones
    """
    cut = data.copy()
    ret = []
    while len(cut):
        roots = [k for k, v in cut.pred.items() if not v]
        if not roots:
            # We can put the cycles off until the end, since they are unreachable they will not be deleted
            # To process the cycles, we pick a node, find the longest path backwards, and then forwards from that node.
            # We repeat this until all nodes are used.
            # Note that since there are no roots, every node in the component *must* be reachable.
            root = next(iter(cut))
            backwards = _edge_bfs(cut, root, networkx.DiGraph.predecessors)
            # No actually the longest in the whole graph, but it is the longest in the component, so it's irrelevant.
            longest = _edge_bfs(cut, backwards[0], networkx.DiGraph.neighbors)
        else:
            longest = max((_edge_bfs(cut, root, networkx.DiGraph.neighbors) for root in roots), key=_score_chain)
        longest.reverse()
        ret.append(longest)
        cut.remove_nodes_from(longest)
    return ret
