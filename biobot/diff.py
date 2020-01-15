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

def diff_forests(forest1, forest2):
    username_changes = []  # Same uid, different username
    username_replacements = []  # This should really be `uid_changes`. Same username, different uid
    gone_uids = []  # Uid left group, or removed username (means it's not stored anymore)
    gone_bios = []  # User removed from bio. Contains (old_parent, new_parent, child_username)
    new_uids = []  # Uid joined group, or added username (means it's stored now)
    new_bios = []  # User added to bio. Contains (old_parent, new_parent, child_username)

    nodes1 = forest1.get_nodes()
    nodes2 = forest2.get_nodes()

    uids1 = {user.uid: user for user in nodes1 if user.uid}
    uids2 = {user.uid: user for user in nodes2 if user.uid}
    all_uids = set(uids1) | set(uids2)

    usernames1 = {user.username.lower(): user for user in nodes1 if user.username}
    usernames2 = {user.username.lower(): user for user in nodes2 if user.username}
    all_usernames = set(usernames1) | set(usernames2)

    for uid in all_uids:
        node1 = uids1.get(uid, None)
        node2 = uids2.get(uid, None)
        if node1 is None:
            new_uids.append(node2)
        elif node2 is None:
            gone_uids.append(node1)
        elif node1.username.lower() != node2.username.lower():
            username_changes.append((node1, node2))
    username_mapping = {node1.username.lower(): node2.username.lower()
                        for node1, node2 in username_changes
                        if node1.username and node2.username}
    gone_uids_usernames = (user.username.lower() for user in gone_uids)
    new_uids_usernames = (user.username.lower() for user in new_uids)

    for uid in all_uids:
        node1 = uids1.get(uid, None)
        node2 = uids2.get(uid, None)
        if node1 and node2:
            children1 = set(child.username.lower() for child in node1.children)
            children2 = set(child.username.lower() for child in node2.children)
            diff1 = children1 - children2
            for gone in diff1:
                mapped = username_mapping.get(gone, None)
                if mapped not in children2:
                    gone_bios.append((node1, node2, gone))
            diff2 = children2 - children1
            for gone in diff2:
                mapped = username_mapping.get(gone, None)
                if mapped not in children1:
                    new_bios.append((node1, node2, gone))

    for username in all_usernames:
        node1 = usernames1.get(username, None)
        node2 = usernames2.get(username, None)
        if (node1 and node2 and node1.uid != node2.uid
              and username not in username_mapping.values() and username not in new_uids_usernames
              and username not in username_mapping.keys() and username not in gone_uids_usernames):
            username_replacements.append((node1, node2))
            try:
                new_uids.remove(node2)
            except ValueError:
                pass
            try:
                gone_uids.remove(node1)
            except ValueError:
                pass

    return (new_uids, gone_uids, username_replacements, username_changes, new_bios, gone_bios)
