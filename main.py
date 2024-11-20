import argparse
import yaml
from scripts.create_site import create_site


def main():
    parser = argparse.ArgumentParser(
        description="Provision new site and switches in NetBox"
    )
    parser.add_argument("config_file", help="Path to YAML configuration file")

    # Получаем аргументы
    args = parser.parse_args()

    # Читаем YAML файл с параметрами
    with open(args.config_file, "r") as file:
        config = yaml.safe_load(file)

    try:
        # Вызываем create_site с параметрами из YAML
        create_site(
            site_name=config["site_name"],
            manufacturer_name=config["manufacturer_name"],
            devices=config["devices"],
            prefix=config["prefix"],
        )
        print(f"Site '{config['site_name']}' with devices successfully created!")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
