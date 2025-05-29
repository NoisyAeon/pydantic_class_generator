from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from configparser import ConfigParser
from pathlib import Path
from typing import List, Optional, Union

import yaml

from pydantic_class_generator.node import Node, ListNode

"""
This module contains the parsers that read and translate a configuration file into nodes.
"""


class ParsingError(Exception):
    """
    Exception raised when an error occurs during parsing.
    """


class NodeParser(ABC):
    """
    Base parser that provides some naming methods.
    """

    @staticmethod
    @abstractmethod
    def is_parsable(path: Path) -> bool:
        """
        Checks if the file at the given path is parsable.

        :param path: the path to the file
        :return: does the parser support the file type
        :rtype: bool
        """
        ...

    @staticmethod
    @abstractmethod
    def _load_file_content(path: Path):
        """
        Loads the content of the file at the given path.

        :param path: the path to the file
        :return: dictionary like object with the content of the file
        """
        ...

    @staticmethod
    def _get_parser(path: Path) -> Optional[NodeParser]:
        """
        Get the correct :class:`.Parser` instance depending on the file type.

        :return: :class:`.Parser` instance or None if the file type is not supported.
        :rtype: NodeParser
        """
        if INIParser.is_parsable(path):
            return INIParser()

        if JSONParser.is_parsable(path):
            return JSONParser()

        if YAMLParser.is_parsable(path):
            return YAMLParser()
        return None

    @staticmethod
    def parse_file(path: Union[str, Path]) -> Optional[Node]:
        """
        Parses the content of the file at the given path.

        :param path: path to the file
        :return: the root :class:`.Node` or None if the file is not parsable.
        :rtype: Node
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist.")

        if path.is_dir():
            raise IsADirectoryError(f"Directory {path} is a directory and not a file.")

        parser = NodeParser._get_parser(path)
        if not parser:
            return None
        try:
            data = parser._load_file_content(path)
            name = path.name.split(".")[0]
            return parser.parse(name=name, data=data)

        except Exception as exc:
            raise ParsingError(f"Error while parsing {path.resolve()}") from exc

    @staticmethod
    def parse_dir(path: Union[str, Path]) -> List[Node]:
        """
        Parses the content of the directory at the given path.

        :param path: path to the directory
        :return: A list with the root :class:`.Node` objects
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist.")

        if not path.is_dir():
            raise NotADirectoryError(f"{path} is not a directory.")

        nodes = []
        for file in path.iterdir():
            if file.is_dir():
                nodes.extend(NodeParser.parse_dir(file))
            else:
                nodes.append(NodeParser.parse_file(file))
        return nodes

    @staticmethod
    def _replace_invalid_characters(name: str, default_character: str) -> str:
        """
        Replace all ä, ö, ü and ß to their counterparts and invalid characters with the given default character.

        :param name: a string containing invalid characters
        :param default_character: the replacement character
        :return: the string without invalid characters
        """
        valid_name = ''
        for char in name:
            if char.lower() == 'ä':
                valid_name += 'ae'
            elif char.lower() == 'ö':
                valid_name += 'oe'
            elif char.lower() == 'ü':
                valid_name += 'ue'
            elif char == 'ß':
                valid_name += 'ss'
            elif char == '_' or char.isdigit() or char.isalpha():
                valid_name += char
            else:
                valid_name += default_character
        return valid_name

    @staticmethod
    def get_valid_class_name(name: str) -> str:
        """
        Get the valid class name in Pascal Case from the given name. If the name starts with a number the prefix 'Model' will be added to the name.

        :param name: the string on which the class name should be based on
        :return: a valid class name
        :rtype: str
        """
        class_name = NodeParser._replace_invalid_characters(name, ' ')

        # underscores indicate snake case
        if '_' in class_name:
            words = []
            for word in class_name.split('_'):
                if not word:
                    continue
                # capitalize() changes the first letter to upper and all others to lower.
                # So its only used if all letters are uppercase so str in Pascal Case is not lost
                if word.isupper():
                    words.append(word.capitalize())
                else:
                    words.append(word[0].upper() + word[1:])
            class_name = ' '.join(words)

        if class_name.isupper():
            class_name = class_name.capitalize()

        # class names can not start with a digit. So Model is added as a prefix
        if not class_name or class_name[0].isdigit():
            class_name = 'Model ' + class_name

        # Change the first letter of each word to uppercase
        return ''.join([word[0].upper() + word[1:] for word in class_name.split(' ') if word])

    @staticmethod
    def get_valid_field_name(name: str) -> str:
        """
        Gat a valid parameter name in snake case. If the name starts with a number the prefix 'field_' will be added to the name.

        :param name: the string on which the field name should be based on
        :return: a valid field name
        :rtype: str
        """
        adjusted_string = NodeParser._replace_invalid_characters(name, '_')

        words = []
        for word in adjusted_string.split('_'):
            if not word:
                continue
            if word.isupper():
                words.append(word.lower())
            else:
                words.append(word)
        field_name = '_'.join(words)

        camel_to_snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')
        field_name = camel_to_snake_case_pattern.sub('_', field_name)

        # parameter names can not start with a digit. So field_ is added as a prefix
        if field_name[0].isdigit():
            field_name = 'field_' + field_name

        return field_name.lower()

    def parse(self, name: str, data: dict) -> Node:
        """
        Parse the given data and return the root :class:`.Node`.

        :param str name: the name of the root node
        :param dict data: the data to be parsed
        :return: the root :class:`.Node`
        :rtype: Node
        """
        root_name = self.get_valid_field_name(name)
        root_type = self.get_valid_class_name(name)
        children = self._get_children_from_dict(data=data, existing_nodes={}, parent_type=root_type)
        return Node(
            name=root_name,
            class_type=root_type,
            children=children,
            original_name=name if name != root_name else None
        )

    def _get_children_from_dict(self, data: dict, existing_nodes: dict, parent_type: str) -> List[Node]:
        """
        Recursively traverse the dict and creates nodes for every element.

        :param data: the dict from which all nodes will be created
        :param existing_nodes: all nodes that have been previously created
        :param parent_type: the class_type of the parent
        :return: a list with the nodes of the current layer of the dict
        :rtype: List[Node]
        """
        children = []
        for field, value in data.items():
            field_name = self.get_valid_field_name(field)

            if isinstance(value, list):
                # lists need special treatment since they generate ListNodes
                babies = self._get_children_from_list(data=value, existing_nodes=existing_nodes, field_name=field_name, parent_type=parent_type)
                children.append(
                    ListNode(
                        name=field_name,
                        class_type='list',
                        children=babies,
                        original_name=field if field != field_name else None
                    )
                )

            else:
                if isinstance(value, dict):
                    # this field has another layer to it -> recursion
                    field_type = self.get_valid_class_name(field)
                    babies = self._get_children_from_dict(data=value, existing_nodes=existing_nodes, parent_type=field_type)

                else:
                    # field has a basic type
                    field_type = type(value).__name__
                    if field_type == 'NoneType':
                        field_type = 'Any'
                    babies = []

                child = Node(
                    name=field_name,
                    class_type=field_type,
                    children=babies,
                    original_name=field if field != field_name else None
                )
                children.append(child)

                # check if the new node is a duplicate or needs its class name adjusted
                self._check_and_adjust_class_type(node=child, existing_nodes=existing_nodes, parent_type=parent_type)

        return children

    def _get_children_from_list(self, data: list, existing_nodes: dict, field_name: str, parent_type: str) -> List[Node]:
        """
        Iterates through the given list and creates Nodes for every element. Recursively calls itself if there is another list in the given list

        :param data: the list to iterate through
        :param existing_nodes: all nodes that have been previously created
        :param field_name: the name of the current field
        :param parent_type: the class type of the parent node
        :return: a list with a Node for every element in the list
        """
        field_type = 'list'
        children = []

        for element in data:
            element_name = self.get_valid_field_name(field_name + "_item")

            if isinstance(element, list):
                babies = self._get_children_from_list(data=element, existing_nodes=existing_nodes, field_name=field_name, parent_type=parent_type)
                child = ListNode(
                    name=element_name,
                    class_type='list',
                    children=babies
                )

            elif isinstance(element, dict):
                # this element has more layers
                element_type = self.get_valid_class_name(field_name + "ListItem")
                babies = self._get_children_from_dict(data=element, existing_nodes=existing_nodes, parent_type=field_type)
                child = Node(
                    name=element_name,
                    class_type=element_type,
                    children=babies
                )
                # there is no direct parent type so no prefix should be added to its class type
                self._check_and_adjust_class_type(node=child, existing_nodes=existing_nodes, parent_type='')

            else:
                class_type = type(element).__name__
                if class_type == 'NoneType':
                    class_type = 'Any'
                # this element has a basic type
                child = Node(
                    name=element_name,
                    class_type=class_type,
                    children=[]
                )

            children.append(child)
        return children

    def _check_and_adjust_class_type(self, node: Node, existing_nodes: dict, parent_type: str) -> None:
        """
        Checks if the given node has an existing class type and marks it as a duplicate.
        If there are name clashes with an already existing class type it adjusts the name of the class type accordingly.

        :param node: the node to check
        :param existing_nodes: all nodes that have been previously created
        :param parent_type: the class type of the parent node
        """
        field_type = node.class_type

        if field_type in existing_nodes:
            # the name of the class is already in use. Check if the class is a duplicate
            for existing in existing_nodes[field_type]:
                if node == existing:
                    node.class_type = existing.class_type
                    node.is_duplicate = True
                    return

            # it is a new class so the name needs to be adjusted
            # add the parent type as a prefix
            node.class_type = self.get_valid_class_name(parent_type + node.class_type)

            # check if the new class type is already in use too
            if any(node.class_type == existing.class_type for existing in existing_nodes[field_type]):
                # add an increasing number to the class type as a suffix
                suffix = len(existing_nodes[field_type])
                node.class_type += str(suffix)

                # Adds a TO DO to the generated code so the user knows this name needs some manual adjustment
                node.needs_adjustment = True

            existing_nodes[field_type].append(node)

        elif node.class_type not in ['int', 'float', 'str', 'bool', 'list', 'tuple', 'Any']:
            # add the node to the collection if the class type is not in use yet and is not a basic type
            existing_nodes[node.class_type] = [node]


class INIParser(NodeParser):
    """
    A parser that reads ini files and parses it into nodes.
    """

    @staticmethod
    def is_parsable(path: Path) -> bool:
        return path.name.endswith('.ini')

    @staticmethod
    def _load_file_content(path: Path) -> ConfigParser:
        config = ConfigParser()
        config.optionxform = str
        config.read(path, encoding='utf-8')
        return config

    def parse(self, name: str, data: ConfigParser) -> Node:

        children = []
        existing_nodes = {}
        for section, value_dict in data.items():
            # no need to parse the DEFAULT section
            if section == "DEFAULT":
                continue

            section_name = self.get_valid_field_name(section)
            section_type = self.get_valid_class_name(section)
            babies = []  # fields of the current section

            for field, value in value_dict.items():
                # try to get the type of the current value
                if value.lower() in ["true", "false"]:
                    field_type = "bool"
                elif value.isdigit():
                    field_type = "int"
                # support , and . for floats. Only one is allowed
                elif value.replace(",", ".").replace(".", "", 1).isdigit():
                    field_type = "float"
                else:
                    field_type = "str"

                field_name = self.get_valid_field_name(field)
                babies.append(
                    Node(
                        name=field_name,
                        class_type=field_type,
                        children=[],
                        original_name=field if field != field_name else None
                    )
                )
            child = Node(
                name=section_name,
                class_type=section_type,
                children=babies,
                original_name=section if section != section_name else None
            )
            self._check_and_adjust_class_type(node=child, existing_nodes=existing_nodes, parent_type='')
            children.append(child)

        root_name = self.get_valid_field_name(name)
        return Node(
            name=root_name,
            class_type=self.get_valid_class_name(name),
            children=children,
            original_name=name if root_name != name else None
        )


class JSONParser(NodeParser):
    """
    A parser that reads json files and parses it  into the :class:`.Node` structure.
    """

    @staticmethod
    def is_parsable(path: Path) -> bool:
        return path.name.endswith('.json')

    def _load_file_content(self, path: Path) -> dict:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)


class YAMLParser(NodeParser):
    """
    A parser that reads yaml files and parses it  into the :class:`.Node` structure.
    """

    @staticmethod
    def is_parsable(path: Path) -> bool:
        return path.name.endswith('.yaml')

    @staticmethod
    def _load_file_content(path: Path) -> dict:
        with open(path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
