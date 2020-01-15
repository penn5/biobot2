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

import itertools


"""Converts the username:bio dict to a tree of users, and optionally a list"""


class Forest:
    def __init__(self):
        self._instances = {}

    def get_roots(self):
        return filter(lambda x: not x.parents, self._instances.values())

    def get_nodes(self):
        return self._instances.values()

    def get_node(self, username, uid=None):
        try:
            ret = self._instances[username.lower()]
            assert uid is None or ret.uid == uid or ret.uid is None
            if uid is not None:
                ret.uid = uid
            return ret
        except KeyError:
            self._instances[username.lower()] = ret = User(self, username)
            ret.uid = uid
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


def make_forest(data):
    if isinstance(data, Forest):
        return data
    forest = Forest()
    for (uid, username), children in data.items():
        if username is not None:
            node = forest.get_node(username, uid)
            for child in children:
                node.add_child(child)
    return forest


def make_trees(data):
    return make_forest(data).get_roots()


def make_chains(data, target):
    forest = make_forest(data)
    leaf = forest.get_node(target)
    ret = _iter_parents(leaf)
    if __debug__:
        ret = list(ret)
        for chain in ret:
            assert len(chain) == len(set(chain)), f"There are duplicate elements in the chain ({chain})"
    return forest, ret


def make_chain(data, target):
    forest, chains = make_chains(data, target)
    return forest, max(chains, key=lambda x: len(x))


def make_all_chains(data):
    """Get a list of chains possible to generate from the data
       Prefers to make longer chains than shorter ones
       Yields lists of Users. Note that they may have incorrect .parents and .children attributes"""
    forest = make_forest(data)
    ignore = []
    ret = []
    while True:
        stacks = itertools.chain.from_iterable(_iter_children(root, ignore=ignore) for root in forest.get_roots())
        try:
            max_stack = max(stacks, key=lambda x: len(x))
        except ValueError:
            break
        ignore.extend(max_stack)
        ret.append(max_stack)
    return forest, ret


def _iter_parents(leaf, current_stack=[], ignore=[]):
    if leaf in ignore:
        return [current_stack]
    new_stack = [leaf] + current_stack
    yielded = False
    for parent in leaf.parents:
        if parent not in current_stack:
            for ret in _iter_parents(parent, new_stack):
                yield ret
                yielded = True
    if not yielded:
        # It's the end of the path. Begin root yields
        yield new_stack


def _iter_children(leaf, current_stack=[], ignore=[]):
    if leaf in ignore:
        return [current_stack]
    new_stack = current_stack + [leaf]
    yielded = False
    for child in leaf.children:
        if child not in current_stack:
            for ret in _iter_children(child, new_stack, ignore):
                yield ret
                yielded = True
    if not yielded:
        # It's the end of the path. Begin leaf yields
        yield new_stack
