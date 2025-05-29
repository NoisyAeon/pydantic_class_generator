from pathlib import Path

from pydantic_class_generator.class_code_generator import generate_class_code, generate_class_code_from_dir, save_to_disk

CONFIG_DIR = Path(__file__).parent.parent / "config_files"
DEMO_DIR = Path(__file__).parent / "demo"


def generate_files():
    """
    Reads the content of configuration files and creates Python files with the BaseModel classes from the data
    """
    # INI File
    generate_class_code(
        input_file=CONFIG_DIR / "ini_connection.ini",
        output_file=DEMO_DIR / "connection_from_ini.py"
    )

    # JSON File
    generate_class_code(
        input_file=CONFIG_DIR / "json_connection.json",
        output_file=DEMO_DIR / "connection_from_json.py"
    )

    # YAML File
    generate_class_code(
        input_file=CONFIG_DIR / "yaml_connection.yaml",
        output_file=DEMO_DIR / "connection_from_yaml.py"
    )

    # Entire directory
    generate_class_code_from_dir(
        input_dir=CONFIG_DIR,
        output_dir=DEMO_DIR / "all_files"
    )


def load_content():
    """
    Creates BaseModel Objects and fills the with the data from configuration files
    """
    from demo.connection_from_ini import load_ini_connection_from_file
    ini_connection = load_ini_connection_from_file(CONFIG_DIR / "ini_connection.ini")

    print(f"ini_connection:\n{ini_connection.model_dump_json(indent=4)}\n\n")

    from demo.connection_from_json import load_json_connection_from_file
    json_connection = load_json_connection_from_file(CONFIG_DIR / "json_connection.json")

    print(f"json_connection:\n{json_connection.model_dump_json(indent=4)}\n\n")

    from demo.connection_from_yaml import load_yaml_connection_from_file
    yaml_connection = load_yaml_connection_from_file(CONFIG_DIR / "yaml_connection.yaml")

    print(f"yaml_connection:\n{yaml_connection.model_dump_json(indent=4)}")

def save_content():
    """
    Creates configuration files from the given BaseModel objects
    """
    from demo.connection_from_ini import load_ini_connection_from_file
    ini_connection = load_ini_connection_from_file(CONFIG_DIR / "ini_connection.ini")

    save_to_disk(data=ini_connection, path=DEMO_DIR/ "generated_config_files" / "config.ini")
    save_to_disk(data=ini_connection, path=DEMO_DIR / "generated_config_files" / "config.json")
    save_to_disk(data=ini_connection, path=DEMO_DIR / "generated_config_files" / "config.yaml")


if __name__ == '__main__':
    generate_files()

    load_content()

    save_content()
