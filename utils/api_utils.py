import logging
import requests
from .config_loader import load_config


NETBOX_URL, HEADERS = load_config("../config.yml")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def api_get(endpoint: str, params: dict) -> dict:
    url = f"{NETBOX_URL}/api/{endpoint}/"
    response = requests.get(url,
                            headers=HEADERS,
                            params=params
                            )
    response.raise_for_status()
    return response.json()


def api_post(endpoint: str, data: dict) -> dict:
    url = f"{NETBOX_URL}/api/{endpoint}/"
    response = requests.post(url,
                             headers=HEADERS,
                             json=data
                             )
    response.raise_for_status()
    return response.json()


def get_object_id(endpoint: str, filters: dict) -> int:
    result = api_get(endpoint, filters)
    objects = result.get("results", [])
    return objects[0]["id"] if objects else None


def create_object(endpoint, data, object_name):
    url = f"{NETBOX_URL}/api/{endpoint}/"

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        if response.status_code == 201:
            object_id = response.json()["id"]
            logger.info(f"{object_name} created successfully with ID: {object_id}")
            return object_id

        elif response.status_code == 400 and "already exists" in response.text:
            object_id = get_object_id(endpoint, {"slug": data.get("slug", "")})
            logger.info(f"Using existing {object_name} with ID: {object_id}")
            return object_id
        else:
            logger.error(f"Unexpected response: {response.status_code}, {response.text}")
            raise ValueError(f"Failed to create {object_name}: {response.text}")
    except ValueError as e:
        logger.error(f"ValueError while creating {object_name}: {e}")
        raise  # Повторно выбрасываем, если нужно дальше обрабатывать
    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating {object_name}: {e}")
        raise


def update_object(endpoint, object_id, data):
    """
    Обновляет объект в NetBox.
    :param endpoint: API endpoint для объекта (например, 'dcim/devices').
    :param object_id: ID объекта, который нужно обновить.
    :param data: Данные для обновления.
    :return: JSON-ответ от API, если успешно, или None.
    """
    url = f"{NETBOX_URL}/api/{endpoint}/{object_id}/"
    response = requests.patch(url, json=data, headers=HEADERS)

    if response.status_code in (200, 204):
        logger.info(f"Successfully updated {endpoint} with ID {object_id}")
        return response.json() if response.status_code == 200 else None
    else:
        logger.error(
            f"Failed to update {endpoint} with ID {object_id}: {response.status_code} - {response.text}"
        )
        return None


def get_manufacturer_id(slug: str):
    """Получаем ID производителя по его slug"""
    url = f"{NETBOX_URL}/api/dcim/manufacturers/?slug={slug}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        manufacturers = response.json().get("results", [])
        if manufacturers:
            return manufacturers[0]["id"]
        else:
            raise ValueError(f"Manufacturer with slug '{slug}' not found.")
    else:
        raise ValueError(f"Failed to fetch manufacturer ID: {response.status_code}")


def create_interface(interface_name, interface_type, device_type_id):
    """
    Создаёт интерфейс для указанного типа устройства, если он ещё не существует.

    :param interface_name: Имя интерфейса.
    :param interface_type: Тип интерфейса.
    :param device_type_id: ID типа устройства.
    """
    # Получить список существующих интерфейсов
    existing_interfaces = get_existing_interfaces(device_type_id)

    if interface_name in existing_interfaces:
        logger.debug(f"Interface '{interface_name}' already exists, skipping.")
        return

    # Создание нового интерфейса
    interface_data = {
        "device_type": device_type_id,
        "name": interface_name,
        "type": interface_type,
    }
    url = f"{NETBOX_URL}/api/dcim/interface-templates/"
    response = requests.post(url, headers=HEADERS, json=interface_data)

    if response.status_code == 201:
        logger.info(f"Interface '{interface_name}' created successfully.")
    else:
        logger.error(f"Failed to create interface: {response.status_code}, {response.text}")


def get_existing_interfaces(device_type_id):
    """
    Получает список существующих интерфейсов для указанного типа устройства.

    :param device_type_id: ID типа устройства.
    :return: Список имён существующих интерфейсов.
    """
    url = f"{NETBOX_URL}/api/dcim/interface-templates/"
    params = {"device_type_id": device_type_id}
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        results = response.json().get('results', [])
        return [iface['name'] for iface in results]
    else:
        logger.error(f"Failed to fetch existing interfaces: {response.status_code}, {response.text}")


def set_primary_ip(device_id, ip_id, ip_version="ipv4"):
    """
    Устанавливает основной IP-адрес для устройства.
    :param device_id: ID устройства.
    :param ip_id: ID IP-адреса.
    :param ip_version: Версия IP ('ipv4' или 'ipv6').
    """
    # Определяем поле для обновления
    primary_ip_field = "primary_ip4" if ip_version == "ipv4" else "primary_ip6"

    # Данные для обновления
    update_data = {primary_ip_field: ip_id}

    # Выполняем обновление устройства
    endpoint = f"dcim/devices/{device_id}/"
    response = requests.patch(
        f"{NETBOX_URL}/api/{endpoint}",
        headers=HEADERS,
        json=update_data,
    )

    if response.status_code == 200:
        logger.info(f"Primary IP for device ID {device_id} set to IP ID {ip_id}.")
    else:
        print(f"Failed to set primary IP: {response.status_code}, {response.text}")
