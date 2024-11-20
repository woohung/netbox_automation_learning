import yaml
from pathlib import Path


def load_config(file_path):
    """
    Загружает конфигурацию из YAML-файла и возвращает константы.

    :param file_path: путь к YAML-файлу.
    :return: кортеж (NETBOX_URL, HEADERS)
    """
    # Определяем абсолютный путь к файлу
    base_dir = Path(__file__).parent
    full_path = base_dir / file_path

    with open(full_path, 'r') as file:
        config = yaml.safe_load(file)
    
    netbox_url = config['netbox']['url']
    api_token = config['netbox']['api_token']
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return netbox_url, headers
