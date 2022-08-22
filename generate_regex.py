#    Bio Bot (Telegram bot for managing the @Bio_Chain_2)
#    Regex parser and converter
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

import collections
import regex
import re

regex_parser_p = re.compile(r"(?<!\\)((?:\\\\)*)\\p(\{\w+?\}|\w)")
regex_parser_P = re.compile(r"(?<!\\)((?:\\\\)*)\\P(\{\w+?\}|\w)")


# see https://www.unicode.org/reports/tr44/#General_Category_Values

# number of characters to consider in the category; must be 1 or 2

# whether to escape all unicode sequences, or only unprintables


def parse_line(line, category_chars):
    split = line.split(";", maxsplit=3)
    end_region = False
    if split[1][0] == "<" and split[1].endswith(", Last>"):
        end_region = True
    return int(split[0], 16), split[2][:category_chars], end_region


def parse_lines(lines, category_chars):
    unassigned = "Cn"[:category_chars]
    lines = iter(lines)
    categories = collections.defaultdict(list)
    ordinal, category, region = parse_line(next(lines), category_chars)
    categories[category] = [0]
    last_ordinal = ordinal
    last_category = category
    synthetic_queue = collections.deque()
    while True:
        if synthetic_queue:
            ordinal, category, end_region = synthetic_queue.popleft()
        else:
            line = next(lines, None)
            if not line:
                break
            ordinal, category, end_region = parse_line(line, category_chars)
        if ordinal != last_ordinal + 1 and not end_region:
            synthetic_queue.extend(((ordinal - 1, unassigned, True), (ordinal, category, end_region)))
            ordinal = last_ordinal + 1
            category = unassigned
        if category != last_category:
            categories[last_category].append(last_ordinal)
            categories[category].append(ordinal)
            last_category = category
        last_ordinal = ordinal

    categories[last_category].append(last_ordinal)
    return categories


def encode_codepoint(codepoint, escape):
    if escape:
        if codepoint <= 0xff:
            return rf"\x{codepoint:02x}"
        if codepoint <= 0xffff:
            return rf"\u{codepoint:04x}"
        if codepoint <= 0xffffffff:
            return rf"\U{codepoint:08x}"
        raise ValueError
    else:
        return re.escape(chr(codepoint))


def iter_regex(ranges, escape_all):
    yield "["
    for start, end in zip(ranges[::2], ranges[1::2]):
        if start == end:
            yield encode_codepoint(start, escape_all)
        elif start + 1 == end:
            yield encode_codepoint(start, escape_all)
            yield encode_codepoint(end, escape_all)
        else:
            yield encode_codepoint(start, escape_all)
            yield "-"
            yield encode_codepoint(end, escape_all)
    yield "]"


def create_regex(ranges, escape_all):
    return "".join(iter_regex(ranges, escape_all))


def iterlines(file):
    while line := file.readline():
        yield line


def generate_regex(regex, categories):
    regex = regex_parser_p.sub(lambda match: match[1] + categories[match[2].strip("{}").casefold()], regex)
    regex = regex_parser_P.sub(lambda match: match[1] + "[^" + categories[match[2].strip("{}").casefold()][1:], regex)
    return regex


def main():
    print("Generating...")
    with open("UnicodeData.txt", "r") as f:
        categories = parse_lines(iterlines(f), 1)
        print(categories)
        f.seek(0)
        categories |= parse_lines(iterlines(f), 2)
    category_regexes = dict(zip((category.casefold() for category in categories), (create_regex(ranges, False) for ranges in categories.values())))
    print(category_regexes)
    print()
    print("\n\n".join(category + "\t" + repr(regex) for category, regex in category_regexes.items()))
    print()
    print("Testing... This will take a few minutes.")
    fail = False
    for category, test in category_regexes.items():
        print("Testing", category)
        expected = regex.compile("\p{" + category + "}", regex.V1)
        test_regex = re.compile(test)
        for ordinal in range(0, 0xE01EF):
            character = chr(ordinal)
            correct = bool(expected.fullmatch(character))
            test_result = bool(test_regex.fullmatch(character))
            if correct != test_result:
                print("FAIL", ordinal, correct, test_result, repr(test))
                fail = True
    if not fail:
        print("Tests succeeded")
    while i := input("Enter your regex: "):
        print(repr(generate_regex(i, category_regexes)))


if __name__ == "__main__":
    main()
