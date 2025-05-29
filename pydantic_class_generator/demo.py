from pathlib import Path

from pydantic_class_generator.class_code_generator import generate_class_code, generate_class_code_from_dir, save_to_disk

CONFIG_DIR = Path(__file__).parent.parent / "config_files"
DEMO_DIR = Path(__file__).parent / "demo"


def generate_files():
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
    from demo.connection_from_ini import load_ini_connection_from_file
    ini_connection = load_ini_connection_from_file(CONFIG_DIR / "ini_connection.ini")

    print(ini_connection)


def save_content():
    pass


if __name__ == '__main__':
    generate_files()

    load_content()

    save_content()
