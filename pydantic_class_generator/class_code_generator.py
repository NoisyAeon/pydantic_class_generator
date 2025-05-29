import json
import os
from configparser import ConfigParser
from pathlib import Path
from typing import List, Union

import yaml
from pydantic import BaseModel

from pydantic_class_generator.node import Node, any_aliases, any_untyped_fields
from pydantic_class_generator.node_parser import NodeParser


def generate_class_code(input_file: Union[str, Path], output_file: Union[str, Path]):
    """
    Reads the configuration file, generates the code and writes it to the output file.

    :param str | Path input_file: The path to the configuration file.
    :param str | Path output_file: The path to the output file.
    """
    root = NodeParser.parse_file(input_file)
    if not root:
        return

    code = generate_all_classes(root)

    if isinstance(output_file, str):
        output_file = Path(output_file)

    if not output_file.parent.exists():
        os.makedirs(output_file.parent)
        with open(output_file.parent / "__init__.py", "w", encoding="utf-8") as file:
            file.write("\n")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)


def generate_class_code_from_dir(input_dir: Union[str, Path], output_dir: Union[str, Path]):
    """
    Reads the configuration files found in the given directory, generates the code and writes it to the output files.

    :param str | Path input_dir: path to the folder with the configuration files.
    :param str | Path output_dir: path to the output folder.
    """
    if isinstance(input_dir, str):
        input_dir = Path(input_dir)

    if isinstance(output_dir, str):
        output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"{input_dir} does not exist.")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"{input_dir} is not a directory.")

    if not output_dir.exists():
        os.makedirs(output_dir)
        with open(output_dir / "__init__.py", "w", encoding="utf-8") as file:
            file.write("\n")
    if not output_dir.is_dir():
        raise NotADirectoryError(f"{output_dir} is not a directory.")

    for file in input_dir.iterdir():
        if file.is_dir():
            generate_class_code_from_dir(file, output_dir)
        else:
            output_file = file.with_suffix(".py")
            generate_class_code(input_file=file, output_file=output_dir.joinpath(output_file.name))


def generate_pydantic_classes(node: Node) -> List[str]:
    """
    Recursive method that calls :meth:`.Node.generate_code` to generate the code for given node and all its children.

    :param Node node: the current node
    :return: list of the generated code of the given node and all its children. Each entry is a new line
    :rtype: List[str]
    """
    if not node.children:
        return []
    generated_code = []

    node_code = node.generate_code()
    if node_code:
        generated_code += node_code
        generated_code.append("")
        generated_code.append("")

    for child in node.children:
        if not child.is_duplicate:
            generated_code += generate_pydantic_classes(child)

    return generated_code


def generate_all_classes(node: Node) -> str:
    """
    Generates all code for the given Node structure, including the header and necessary imports

    :param node: the root node
    :return: a string with all code
    :rtype: str
    """

    generated_code = (
        [
            f'"""\nA collection of generated BaseModels with {node.class_type} as the root.\n"""',
            "",
            "from __future__ import annotations",
            "",
            "from pathlib import Path"
        ]
    )
    typing_import = "from typing import Union"
    if any_untyped_fields(node):
        typing_import += ", Any"
    generated_code.append(typing_import)

    pydantic_imports = "\nfrom pydantic import BaseModel"

    # Only import AliasChoices if its actually needed
    if any_aliases(node):
        pydantic_imports += ", Field, AliasChoices"

    generated_code.append(pydantic_imports)

    generated_code.append("\nfrom pydantic_class_generator.class_code_generator import configuration_file_to_dict")

    generated_code.append("\n")
    generated_code += generate_pydantic_classes(node)

    # simple method to convert a dict to the pydantic object
    generated_code += [
        f'def load_{node.name}(input_dict: dict) -> {node.class_type}:',
        f'    """',
        f'    Returns a :class:`.{node.class_type}` with the value of the given input dictionary.',
        f'    """',
        f'    return {node.class_type}(**input_dict)',
        '',
        ''
    ]

    # method to read the configuration data from a file
    generated_code += [
        f'def load_{node.name}_from_file(path: Union[str, Path], encoding: str = "utf-8") -> {node.class_type}:',
        f'    """',
        f'    Reads the content of the given file and returns a :class:`.{node.class_type}`',
        f'    """',
        '    try:',
        '        data = configuration_file_to_dict(path=path, encoding=encoding)',
        f'        return load_{node.name}(data)',
        '    except Exception as exc:',
        '        # This is intentionally this way to get a prettier traceback',
        '        raise exc from Exception(f"Failed to load data from {path}")',
        ''
    ]

    return "\n".join(generated_code)


def configuration_file_to_dict(path: Union[str, Path], encoding: str = 'utf-8') -> dict:
    """
    Converts a configuration file into a dictionary.

    :param str | Path path: Path to the configuration file.
    :param str encoding: Encoding of the configuration file. Default: utf-8.
    :return: a dictionary with the content of th configuration file.
    """
    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File {path} does not exist.")

    if path.is_dir():
        raise IsADirectoryError(f"Directory {path} is a directory and not a file.")

    if path.name.endswith('ini'):
        config = ConfigParser()
        config.optionxform = str
        config.read(path, encoding=encoding)
        return {key: dict(value) for key, value in config.items()}

    elif path.name.endswith('yaml'):
        with open(path, 'r', encoding=encoding) as file:
            data = yaml.safe_load(file)
            return data

    elif path.name.endswith('json'):
        with open(path, 'r', encoding=encoding) as file:
            data = json.load(file)
            return data
    return {}


def save_to_disk(data: BaseModel, path: Union[str, Path]) -> None:
    if isinstance(path, str):
        path = Path(path)

    if not path.parent.exists():
        os.makedirs(path.parent)

    if path.name.endswith('.ini'):
        _save_ini_file(data, path)
    elif path.name.endswith('.json'):
        _save_json_file(data, path)
    elif path.name.endswith('.yaml'):
        _save_yaml_file(data, path)
    else:
        raise ValueError(f'The given path {path} does not have an extension ".ini", ".json" or ".yaml"')


def _save_ini_file(data: BaseModel, path: Path) -> None:
    dump = data.model_dump(by_alias=True)
    config_parser = ConfigParser()
    config_parser.optionxform = str
    for section, section_dict in dump.items():
        config_parser[section] = section_dict
    with open(path, "w", encoding="utf-8") as file:
        config_parser.write(file)


def _save_json_file(data: BaseModel, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(data.model_dump_json(indent=2))


def _save_yaml_file(data: BaseModel, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(yaml.dump(data.model_dump(by_alias=True), default_flow_style=False))
