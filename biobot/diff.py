#    Bio Bot (Telegram bot for managing the @Bio_Chain_2)
#    Copyright (C) 2022 Hackintosh Five

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


import io
import logging
import operator

import matplotlib as mpl
import networkx as nx
import numpy as np
import scipy.spatial
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from .chain import make_chain
from .user import node_to_user

logger = logging.getLogger("diff")

mpl.rcParams["svg.fonttype"] = "none"  # render fonts as text to make the svg searchable


# names must always be unique


def _default_namer(user, full):
    if not user.usernames:
        ret = str(user.id)
    elif full and user.id:
        ret = (
            ", ".join(username.casefold() for username in user.usernames)
            + f"({user.id})"
        )
    else:
        ret = ", ".join(username.casefold() for username in user.usernames)
    if user.deleted:
        ret += "⌫"
    if not user.id:
        ret += "⯑"
    return ret


def _linking_namer(user, full):
    if not user.id:
        ret = ",".join(
            f'<a href="https://t.me/{username}">{username}</a>'
            for username in user.usernames
        )
    elif full and user.usernames and user.id:
        ret = (
            ",".join(
                f'<a href="https://t.me/{username}">{username}</a>'
                for username in user.usernames
            )
            + f' (<a href="tg://user?id={user.id}">{user.id}</a>)'
        )
    elif user.usernames:
        ret = ",".join(
            f'<a href="tg://user?id={user.id}">{username}</a>'
            for username in user.usernames
        )
    else:
        ret = f'<a href="tg://user?id={user.id}">{user.id}</a>'
    if user.deleted:
        ret += "⌫"
    if not user.id:
        ret += "⯑"
    return ret


def _usernames_to_str(usernames):
    return (
        ",".join(sorted(username.casefold() for username in usernames))
        if usernames
        else None
    )


def _graph_to_dict(data):
    ret = {}
    names = {}
    for name, children in data.adjacency():
        node = data.nodes[name]
        uid = node["uid"]
        usernames = _usernames_to_str(node["usernames"])
        ret[(uid, usernames)] = {
            _usernames_to_str(data.nodes[child]["usernames"]) for child in children
        }
        ret[(uid, usernames)].discard(usernames)
        names[(uid, usernames)] = name
    return ret, names


def _generate_diff_data(old_graph, new_graph, namer, ignore_edits):
    old_data, old_map = _graph_to_dict(old_graph)
    new_data, new_map = _graph_to_dict(new_graph)

    old_uid_to_usernames = {
        uid: usernames
        for uid, usernames in old_data.keys()
        if uid is not None and usernames is not None
    }
    new_uid_to_usernames = {
        uid: usernames
        for uid, usernames in new_data.keys()
        if uid is not None and usernames is not None
    }
    old_usernames_to_uid = {
        usernames: uid
        for uid, usernames in old_data.keys()
        if uid is not None and usernames is not None
    }

    duplicate_uids = set()
    duplicate_usernames = set()
    for uid, usernames in new_data.keys():
        if uid is not None and old_uid_to_usernames.get(uid, False) not in (
            usernames,
            False,
        ):
            duplicate_uids.add(uid)
        if usernames is not None and old_usernames_to_uid.get(usernames, False) not in (
            uid,
            False,
        ):
            duplicate_usernames.add(usernames)

    old_names = {
        usernames
        or uid: namer(
            node_to_user(old_graph.nodes[old_map[(uid, usernames)]]),
            full=uid in duplicate_uids or usernames in duplicate_usernames,
        )
        for uid, usernames in old_data
    }
    new_names = {
        usernames
        or uid: namer(
            node_to_user(new_graph.nodes[new_map[(uid, usernames)]]),
            full=uid in duplicate_uids or usernames in duplicate_usernames,
        )
        for uid, usernames in new_data
    }

    old_edges = {
        (old_names[username or uid], old_names.setdefault(child, child))
        for (uid, username), children in old_data.items()
        for child in children
    }
    new_edges = {
        (new_names[username or uid], new_names.setdefault(child, child))
        for (uid, username), children in new_data.items()
        for child in children
    }
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
        old_name = old_names[old_uid_to_usernames.get(uid, uid)]
        new_name = new_names[new_uid_to_usernames.get(uid, uid)]
        uid_edges.add((old_name, new_name))
        if ignore_edits:
            common_names.add(old_name)
            common_names.add(new_name)
            old_only_names.discard(old_name)
            new_only_names.discard(new_name)

    for usernames in duplicate_usernames:
        old_name = old_names[usernames]
        new_name = new_names[usernames]
        username_edges.add((old_name, new_name))
        if ignore_edits:
            common_names.add(old_name)
            common_names.add(new_name)
            old_only_names.discard(old_name)
            new_only_names.discard(new_name)

    return (
        common_edges,
        old_only_edges,
        new_only_edges,
        uid_edges,
        username_edges,
        common_names,
        old_only_names,
        new_only_names,
        old_names,
        new_names,
    )


def _generate_diff_graph(old_data, new_data, namer, ignore_edits):
    (
        common_edges,
        old_only_edges,
        new_only_edges,
        uid_edges,
        username_edges,
        common_names,
        old_only_names,
        new_only_names,
        old_names,
        new_names,
    ) = _generate_diff_data(old_data, new_data, namer, ignore_edits)
    graph = nx.DiGraph()

    for name in common_names:
        graph.add_node(name, type="common")
    for name in old_only_names:
        graph.add_node(name, type="old")
    for name in new_only_names:
        graph.add_node(name, type="new")

    for src, dest in old_only_edges:
        graph.add_edge(src, dest, type="old", weight=0.5)
    for src, dest in new_only_edges:
        graph.add_edge(src, dest, type="new", weight=0.5)
    for src, dest in common_edges:
        graph.add_edge(src, dest, type="common", weight=1)
    for src, dest in uid_edges:
        graph.add_edge(src, dest, type="uid", weight=1.5)
    for src, dest in username_edges:
        graph.add_edge(src, dest, type="username", weight=1.5)

    return (
        graph,
        common_edges,
        old_only_edges,
        new_only_edges,
        uid_edges,
        username_edges,
        common_names,
        old_only_names,
        new_only_names,
        old_names,
        new_names,
    )


def textual_chain_diff(old_data, new_data, directed_delim, line_delim):
    (
        _,
        old_only_edges,
        new_only_edges,
        uid_edges,
        username_edges,
        _,
        old_only_names,
        new_only_names,
        _,
        _,
    ) = _generate_diff_data(old_data, new_data, _linking_namer, True)
    old_only_edges = line_delim.join(
        directed_delim.join(edge) for edge in old_only_edges
    )
    new_only_edges = line_delim.join(
        directed_delim.join(edge) for edge in new_only_edges
    )
    uid_edges = line_delim.join(directed_delim.join(edge) for edge in uid_edges)
    username_edges = line_delim.join(
        directed_delim.join(edge) for edge in username_edges
    )
    old_only_names = line_delim.join(old_only_names)
    new_only_names = line_delim.join(new_only_names)
    return (
        old_only_edges,
        new_only_edges,
        uid_edges,
        username_edges,
        old_only_names,
        new_only_names,
    )


def draw_chain_diff(old_data, new_data, target, format, extension=None):
    dpi = 100

    ideal_gap = 0.8 * dpi
    minimum_sibling_gap = 0.4 * dpi

    (
        graph,
        common_edges,
        old_only_edges,
        new_only_edges,
        uid_edges,
        username_edges,
        common_names,
        old_only_names,
        new_only_names,
        old_names,
        new_names,
    ) = _generate_diff_graph(old_data, new_data, _default_namer, False)

    if target:
        old_chain = [
            old_names[_usernames_to_str(user.usernames)]
            for user in make_chain(old_data, target)
        ]
        old_chain = [
            (old_chain[i], old_chain[i + 1]) for i in range(len(old_chain) - 1)
        ]
        new_chain = [
            new_names[_usernames_to_str(user.usernames)]
            for user in make_chain(new_data, target)
        ]
        new_chain = [
            (new_chain[i], new_chain[i + 1]) for i in range(len(new_chain) - 1)
        ]

    for source, dest, data in graph.edges.data():
        distance = 10
        distance -= data["weight"]
        if "⯑" in source or "⯑" in dest:
            # people not in the chain group have a low emphasis for layout
            distance += 1
        if target:
            if (source, dest) in old_chain or (source, dest) in new_chain:
                # people in the chain have a high emphasis for layout
                distance -= 1
        data["layout_weight"] = distance / 10

    components = set(frozenset(c) for c in nx.weakly_connected_components(graph))

    component_pos = {}
    component_pos_v = {}
    for component in components:
        sg = graph.subgraph(component)
        edges = sg.edges()
        if len(sg) <= 2:
            # avoid expensive layout function and just put the nodes next to each other
            this_component_pos = {
                n: np.array((i, 0), dtype=np.float64) for i, n in enumerate(sg)
            }
        else:
            # shortest weighted undirected path in the component
            dist = dict(
                nx.shortest_path_length(
                    nx.classes.graphviews.generic_graph_view(sg, nx.Graph),
                    weight="layout_weight",
                )
            )
            logger.debug(dist)
            this_component_pos = nx.kamada_kawai_layout(sg, dist=dist)
        if edges:
            # the shortest gap between any pair of neighbour nodes shall be ideal_gap
            scale = ideal_gap / (
                sum(
                    np.linalg.norm(
                        this_component_pos[dest] - this_component_pos[source]
                    )
                    for source, dest in edges
                )
                / len(edges)
            )
            logger.debug("Component %r scale %r", component, scale)
            this_component_pos_v = np.array(list(this_component_pos.values()))
            max_size = dpi * len(component)
            old_size = np.ptp(this_component_pos_v, axis=0)
            if np.any(np.greater(old_size * scale, max_size)):
                logger.warning(
                    "Component scale %r too high (range %r, max %r)",
                    scale,
                    old_size,
                    max_size,
                )
                scale = np.min(max_size / old_size)
            this_component_pos_v *= scale

            # rotate to flat position
            # find the furthest pair of points
            distances = scipy.spatial.distance.pdist(this_component_pos_v)
            furthest_index = np.argmax(distances)
            furthest_distance = distances[furthest_index]
            del distances
            vecs = np.array(np.triu_indices(this_component_pos_v.shape[0], k=1))[
                :, furthest_index
            ]
            left, right = this_component_pos_v[vecs]
            del vecs
            cosine, sine = (right - left) / furthest_distance
            mat = np.array([[cosine, -sine], [sine, cosine]])
            np.matmul(this_component_pos_v, mat, out=this_component_pos_v)

        if len(sg) <= 2:
            # we don't need to check for negative coordinates if there are no edges, because we created the coordinates ourselves

            component_pos[component] = this_component_pos
            component_pos_v[component] = this_component_pos.values()
        else:
            mins = np.amin(this_component_pos_v, axis=0)
            this_component_pos_v -= mins  # remove negative coordinates

            scaled = dict(zip(this_component_pos, this_component_pos_v))
            component_pos[component] = scaled
            component_pos_v[component] = this_component_pos_v.tolist()

    logger.debug("All components prepared. Laying out...")
    component_off = dict(
        zip(component_pos, pack_components(component_pos_v.values(), ideal_gap))
    )
    logger.debug("Components laid out. Preparing for drawing...")
    # apply offsets from packing to the node locations
    pos = {}
    for component, (x, y) in component_off.items():
        this_component_pos = component_pos[component]
        for node, node_pos in this_component_pos.items():
            pos[node] = node_pos[0] + x, node_pos[1] + y

    max_x = max(map(operator.itemgetter(0), pos.values()))
    max_y = max(map(operator.itemgetter(1), pos.values()))

    # draw
    fig = Figure(figsize=(max_x / dpi, max_y / dpi), dpi=dpi)
    # turn off most of the padding
    # there's still some padding left from somewhere, but that's fine ¯\_(ツ)_/¯
    fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    ax = fig.subplots()
    ax.axis("off")
    ax.margins(0)

    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=common_names, node_color="tab:blue", node_size=20
    )
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=old_only_names, node_color="tab:red", node_size=20
    )
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=new_only_names, node_color="tab:green", node_size=20
    )
    if target:
        nx.draw_networkx_edges(
            graph,
            pos,
            ax=ax,
            edgelist=new_chain,
            width=6,
            alpha=0.1,
            edge_color=np.linspace(0, 1, len(new_chain)),
            edge_cmap=plt.get_cmap("cool"),
        )
        nx.draw_networkx_edges(
            graph,
            pos,
            ax=ax,
            edgelist=old_chain,
            width=6,
            alpha=0.1,
            edge_color=np.linspace(0, 1, len(old_chain)),
            edge_cmap=plt.get_cmap("autumn"),
        )
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=common_edges,
        width=2,
        alpha=0.5,
        edge_color="tab:blue",
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=new_only_edges,
        width=2,
        alpha=0.5,
        edge_color="tab:green",
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=old_only_edges,
        width=2,
        alpha=0.5,
        edge_color="tab:red",
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=uid_edges,
        width=2,
        alpha=0.5,
        edge_color="tab:orange",
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        ax=ax,
        edgelist=username_edges,
        width=2,
        alpha=0.5,
        edge_color="tab:pink",
    )
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=5)
    data = io.BytesIO()
    data.name = "chain." + (extension or format)

    # we use a heuristic bbox because "tight" is very slow
    bbox = mpl.transforms.Bbox.from_extents(0, 0, max_x / dpi, max_y / dpi)
    fig.savefig(data, dpi=dpi, bbox_inches=bbox, format=format)
    data.seek(0)
    return data


# inlined
# def check(grid, x, y):
#     if __debug__:
#         try:
#             return grid[y] & 1 << x
#         except IndexError:
#             return 0
#     else:
#         try:
#             return grid[y] & 1 << x
#         except:  # IndexError
#             return 0


# inlined
# def mark(grid, x, y):
#     if __debug__:
#         try:
#             grid[y] |= 1 << x
#         except IndexError:
#             if y - len(grid) >= 1000:
#                 logger.warning("Very large grid expansion detected. State: grid=%r, x,y=%r,%r", grid, x, y)
#             for _ in range(len(grid), y):
#                 grid.append(0)
#             assert y == len(grid)
#             grid.append(1 << x)
#     else:
#         try:
#             grid[y] |= 1 << x
#         except:  # IndexError, SystemError or MemoryError but System/MemoryError is rethrown upon retry
#             for _ in range(len(grid), y):
#                 grid.append(0)
#             grid.append(1 << x)


def conv(x, y, padding):
    return int(x // padding), int(y // padding)


def unconv(x, y, padding):
    return x * padding, y * padding


def pad(x, y):
    if x and y:  # they're >=1, so we can subtract 1
        return {
            (x - 1, y - 1),
            (x, y - 1),
            (x + 1, y - 1),
            (x - 1, y),
            (x, y),
            (x + 1, y),
            (x - 1, y + 1),
            (x, y + 1),
            (x + 1, y + 1),
        }
    elif x:
        return {
            (x - 1, y),
            (x, y),
            (x + 1, y),
            (x - 1, y + 1),
            (x, y + 1),
            (x + 1, y + 1),
        }
    elif y:
        return {
            (x, y - 1),
            (x + 1, y - 1),
            (x, y),
            (x + 1, y),
            (x, y + 1),
            (x + 1, y + 1),
        }
    else:
        return {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}


def coord_iter():
    """
    Iterate coordinates, avoiding the edges. See photo at https://t.me/ProgrammersFromPlag/73148
    """
    yield (0, 0)
    side_length = 1
    coord = [1, 0]
    while True:
        yield coord
        if coord[0] == side_length:
            if coord[1] == side_length - 1:
                coord = [0, side_length]
            elif coord[1] == side_length:
                side_length += 1
                coord = [side_length, 0]
            else:
                coord[1] += 1
        else:
            assert coord[1] == side_length
            coord[0] += 1


if __debug__:

    def render_grid(grid, results, component_pos, padding):
        length = max(row.bit_length() for row in grid)
        filled = {
            conv(result[0] + x, result[1] + y, padding)
            for result, nodes in zip(results, component_pos)
            for x, y in nodes
            if result
        }
        ret = [str(filled)]
        for i, row in enumerate(grid):
            ret.append(
                " ".join(
                    "🞓" if (j, i) in filled else "🞔" if row & 1 << j else "🞎"
                    for j in range(length)
                )
            )
        return "\n".join(ret)


def pack_components(component_pos, padding):
    grid = [0]  # each row is a bitmask, 0=free

    results = [None] * len(component_pos)
    # iterate components largest-to-smallest, keeping track of order
    for component, nodes in sorted(
        enumerate(component_pos), key=lambda x: len(x[1]), reverse=True
    ):
        converted = {conv(x, y, padding) for x, y in nodes}
        if __debug__:
            debug_counter = 0
        for i, j in coord_iter():
            if __debug__:
                if debug_counter == 1000:
                    logger.warning(
                        "Very large grid iteration detected. State: i,j=%r,%r, component=%r, counter=%r, converted=%r, grid=%r, results=%r, component_pos=%r, padding=%r",
                        i,
                        j,
                        component,
                        debug_counter,
                        converted,
                        grid,
                        results,
                        component_pos,
                        padding,
                    )
                    debug_counter = 0
                debug_counter += 1
            for x, y in converted:
                # inlined: if check(grid, x + i, y + j): break
                if __debug__:
                    try:
                        if grid[y + j] & 1 << (x + i):
                            break
                    except IndexError:
                        pass
                else:
                    try:
                        if grid[y + j] & 1 << (x + i):
                            break
                    except:  # IndexError
                        pass
            else:
                # we found a valid place, let's use it
                for x, y in set.union(*(pad(x, y) for x, y in converted)):
                    # inlined: mark(grid, x + i, y + j)
                    if __debug__:
                        try:
                            grid[y + j] |= 1 << (x + i)
                        except IndexError:
                            if (y + j) - len(grid) >= 1000:
                                logger.warning(
                                    "Very large grid expansion detected. State: grid=%r, x,y=%r,%r",
                                    grid,
                                    x + i,
                                    y + j,
                                )
                            for _ in range(len(grid), y + j):
                                grid.append(0)
                            assert y + j == len(grid)
                            grid.append(1 << (x + i))
                    else:
                        try:
                            grid[y + j] |= 1 << (x + i)
                        except:  # IndexError, SystemError or MemoryError but System/MemoryError is rethrown upon retry
                            for _ in range(len(grid), y + j):
                                grid.append(0)
                            grid.append(1 << (x + i))
                location = i, j
                break
        # coordinates are generated infinitely so at the end of this loop, we have a valid location
        results[component] = unconv(*location, padding)
        if __debug__:
            logger.log(0, render_grid(grid, results, component_pos, padding))
    return results
