from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

"""
This module contains the Nodes, an intermediate data structure that knows its direct children and is able to generate code for a pydantic class representing 
itself, and methods for the code generation of an entire configuration file.
"""


@dataclass
class Node:
    """
    A class that represents a section or field in the configuration file.

    Attributes:
        name (str): This name will be used as the parameter name in any parent class. Therefore, it should be in snake case.
        class_type (str): This name will be used as the class name. It should be in upper Pascal Case
        children (List[Node]): This list contains the children nodes of the section or field in the configuration file.
        default (Optional[str]): The default value for the class attribute.
        is_duplicate (bool): Marks the node as a duplicate
        needs_adjustment (bool): adds a TO DO to the generated code.
    """
    name: str
    class_type: str
    children: List['Node']
    default: Optional[str] = None
    original_name: Optional[str] = None
    is_duplicate: bool = False
    needs_adjustment: bool = False

    @property
    def _field_args(self) -> str:
        """
        Returns the default value and AliasChoices
        """
        args = []
        if self.default:
            args.append(self.default)
        if self.original_name:
            args.append(f"\n        alias='{self.original_name}',\n        validation_alias=AliasChoices('{self.name}', '{self.original_name}')")
        return ', '.join(args)

    def __post_init__(self):
        """
        Validates if the name and class_type are valid python identifiers.
        """
        if not self.name.isidentifier():
            raise ValueError(f'"{self.name}" is not a valid identifier! Name in file: {self.original_name}')
        if "list" not in self.class_type and not self.class_type.isidentifier():
            raise ValueError(f'"{self.class_type}" is not a valid class name!')

    def __eq__(self, other: Node) -> bool:
        """
        Checks if two nodes are equal by comparing the start of the class_type and all children.
        """
        if not isinstance(other, Node):
            return False

        # The class_type might contain a number at the end which should be disregarded
        if (not (other.class_type.startswith(self.class_type) or self.class_type.startswith(other.class_type)) or self.name != other.name or
                len(self.children) != len(other.children)):
            return False

        # The order of the fields is not important for equality
        sorted_children = sorted(self.children, key=lambda n: n.name)
        sorted_other = sorted(other.children, key=lambda n: n.name)
        for i in range(len(sorted_children)):
            if not sorted_children[i] == sorted_other[i]:
                return False
        return True

    def generate_code(self) -> List[str]:
        """
        Generates the code for the pydantic class based on this node

        :return: A list containing the generated code where each entry is a new line
        :rtype: List[str]
        """
        if not self.children:
            return []
        source_code = []
        if self.needs_adjustment:
            source_code.append("# TODO please adjust the class name")
        source_code.extend([
            f"class {self.class_type}(BaseModel):",
            '    """',
            f'    Pydantic class for {self.original_name if self.original_name else self.class_type}',
            f'    """'
        ])
        for child in self.children:
            if child.class_type == 'Any':
                source_code.append(f"    # TODO please specify the type")
            line = f"    {child.name}: {child.class_type}"
            if child._field_args:
                line += f" = Field({child._field_args})"
                source_code.append(line)
                source_code.append('')
            else:
                source_code.append(line)
        if not source_code[-1]:
            source_code = source_code[:-1]
        return source_code


class ListNode(Node):
    """
    A class that represents a list in the configuration file.
    """
    _class_type: str = field(init=False, repr=False)

    @property
    def class_type(self):
        """
        Returns the type as a string.

        :return: 'list' if there are no children; 'list[<t>]' if all children share the samy type; 'list[Union[<t1>, <t2>, ...]' otherwise.
        :rtype: str
        """
        if not self.children:
            return "list"
        types = list({child.class_type: None for child in self.children})
        if len(types) == 1:
            return f"list[{self.children[0].class_type}]"
        return "list[Union[" + ", ".join(types) + "]]"

    @class_type.setter
    def class_type(self, value):
        self._class_type = value

    def generate_code(self) -> List[str]:
        """
        A list node doesn't represent a new class so no code will be generated.

        :return: an empty list
        :rtype: list
        """
        return []


def any_unions(node: Node) -> bool:
    """
    Recursively checks if the given node or any of its children has a union as its type.

    :param node: the current node
    :return: Are there any unions
    :rtype: bool
    """
    if isinstance(node, ListNode):
        # It is not a union if the ListNode is just a List where every child has the samy type
        if "Union" in node.class_type:
            return True

    for child in node.children:
        if any_unions(child):
            return True

    return False


def any_untyped_fields(node: Node) -> bool:
    """
    Recursively checks if the given node or any of its children has no type.

    :param node: the current node
    :return: Are there any unions
    :rtype: bool
    """
    if node.class_type == 'Any':
        return True

    for child in node.children:
        if any_untyped_fields(child):
            return True

    return False


def any_aliases(node: Node) -> bool:
    """
    Recursively checks if the given node or any of its children has an alias name.

    :param node: the current node
    :return: Are there any aliases
    :rtype: bool
    """
    if node.original_name:
        return True

    for child in node.children:
        if any_aliases(child):
            return True

    return False
