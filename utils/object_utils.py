import ipaddress
import logging

from .api_utils import (
    set_primary_ip,
    api_get,
    create_object,
    get_object_id,
    update_object,
)
from .utils import create_interface_templates, _slugify

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_or_get_site(site_name):
    site_slug = _slugify(site_name)
    site_id = get_object_id("dcim/sites", {"slug": site_slug})

    if not site_id:
        site_data = {"name": site_name, "slug": site_slug}
        site_id = create_object("dcim/sites", site_data, f"Site '{site_name}'")
    else:
        logger.info(f"Using existing site '{site_name}' with ID: {site_id}")

    return site_id


def create_or_get_manufacturer(manufacturer_name):
    manufacturer_slug = _slugify(manufacturer_name)
    manufacturer_id = get_object_id("dcim/manufacturers", {"slug": manufacturer_slug})

    if not manufacturer_id:
        manufacturer_data = {"name": manufacturer_name, "slug": manufacturer_slug}
        manufacturer_id = create_object(
            "dcim/manufacturers",
            manufacturer_data,
            f"Manufacturer '{manufacturer_name}'",
        )
    else:
        logger.info(
            f"Using existing manufacturer '{manufacturer_name}' with ID: {manufacturer_id}"
        )

    return manufacturer_id


def create_or_get_device_type(manufacturer_id, model_name, interfaces=[]):
    device_type_slug = _slugify(model_name)
    device_type_id = get_object_id(
        "dcim/device-types", {"manufacturer_id": manufacturer_id, "model": model_name}
    )

    if not device_type_id:
        device_type_data = {
            "manufacturer": manufacturer_id,
            "model": model_name,
            "slug": device_type_slug,
            "is_full_depth": False,
        }
        device_type_id = create_object(
            "dcim/device-types", device_type_data, f"Device type '{model_name}'"
        )
        logger.info(f"Created new device type '{model_name}' with ID: {device_type_id}")
    else:
        logger.info(f"Using existing device type '{model_name}' with ID: {device_type_id}")

    # Создаем интерфейсы для каждого типа, определенного в списке interfaces
    if interfaces:
        for interface in interfaces:
            interface_range = interface["interface_range"]
            interface_type = interface["interface_type"]
            create_interface_templates(device_type_id, interface_range, interface_type)
    else:
        logger.info(f"The list {interfaces} might be empty.")
        pass
    return device_type_id


def create_or_get_device_role(role_name, color=None):
    role_slug = _slugify(role_name)
    role_id = get_object_id("dcim/device-roles", {"slug": role_slug})

    if not role_id:
        role_data = {"name": role_name, "slug": role_slug}
        if color:
            role_data["color"] = color

        role_id = create_object(
            "dcim/device-roles", role_data, f"Device role {role_name}"
        )
    else:
        logger.info(f"Using existing role '{role_name}' with ID: {role_id}")

    return role_id


def create_device(device_name, device_type_id, role_id, site_id):
    """
    Создает устройство.
    :param device_name: Имя устройства.
    :param device_type_id: ID типа устройства.
    :param role_id: ID роли устройства.
    :param site_id: ID сайта.
    :param interfaces: Список интерфейсов (включая vlan).
    :return: ID созданного устройства.
    """
    device_data = {
        "name": device_name,
        "device_type": device_type_id,
        "role": role_id,
        "site": site_id,
    }

    device_id = create_object("dcim/devices", device_data, f"Device {device_name}")
    if not device_id:
        logger.error(f"Failed to create device '{device_name}'")
        return None

    logger.info(f"Created device '{device_name}' with ID: {device_id}")
    return device_id


def create_or_get_prefix(prefix, status="active"):
    prefix_id = get_object_id("ipam/prefixes", {"prefix": prefix})

    if not prefix_id:
        prefix_data = {"prefix": prefix, "status": status}
        prefix_id = create_object("ipam/prefixes", prefix_data, f"Prefix {prefix}")
    else:
        logger.info(f"Using existing prefix '{prefix}' with ID: {prefix_id}")

    return prefix_id


def create_or_get_ip_address(address, description="", status="active"):
    address_id = get_object_id("ipam/ip-addresses", {"address": address})
    if not address_id:
        address_data = {
            "address": address,
            "status": status,
            "description": description,
        }
        address_id = create_object(
            "ipam/ip-addresses", address_data, f"Address {address}"
        )
    else:
        logger.info(f"Using existing prefix '{address}' with ID: {address_id}")

    return address_id


def find_free_ip_addresses(subnet, device_names, count):
    """
    Находит первые свободные IP-адреса в указанной подсети.
    :param subnet: Подсеть в формате '192.168.1.0/24'.
    :param count: Количество IP-адресов, которые нужно найти.
    :param device_names: Список имен устройств для привязки к IP (опционально).
    :return: Список ID созданных или найденных IP-адресов.
    """
    # Получаем список всех IP-адресов в подсети из NetBox
    ip_list = api_get("ipam/ip-addresses", {"parent": subnet}).get("results", [])
    used_ips = {ip["address"].split("/")[0] for ip in ip_list}
    # Генерируем все возможные адреса в подсети
    network = ipaddress.ip_network(subnet)
    free_ips = []
    for ip in network.hosts():  # Перебираем только адреса для хостов
        if str(ip) not in used_ips:
            free_ips.append(str(ip))
            if len(free_ips) == count:  # Нашли достаточно адресов
                break
    if len(free_ips) < count:
        raise ValueError(f"Not enough free IP addresses in subnet {subnet}")
    # Собираем список из свободных IP-адресов
    ip_ids = []
    for _, ip in enumerate(free_ips):
        ip_ids.append(
            create_or_get_ip_address(
                f"{ip}/{network.prefixlen}",
            )
        )

        return ip_ids


def find_available_device_name(site_name, suffix, count):
    # Начинаем с индекса 1 и продолжаем до тех пор, пока не найдем нужное количество доступных имен
    device_names = []
    index = 1
    while len(device_names) < count:
        device_name = f"{site_name}-{suffix}-{index:02d}"
        if not get_object_id("dcim/devices", {"name": device_name}):
            device_names.append(device_name)
        index += 1
    return device_names


def allocate_ip_to_device_interface(
    device_id, interface_name, subnet, device, description, count
):
    """
    Ищет, создает и назначает IP-адрес на интерфейс устройства.
    :param device_id: ID устройства.
    :param interface_name: Имя интерфейса устройства.
    :param subnet: Подсеть для поиска IP-адреса.
    :param description: Описание IP-адреса.
    :return: ID созданного или назначенного IP-адреса.
    """
    try:
        # Находим свободный IP в подсети
        free_ip_addresses = []
        free_ips = find_free_ip_addresses(subnet, device, count)
        if free_ips:
            for i in free_ips:
                free_ip_addresses.append(
                    api_get("ipam/ip-addresses", {"id": i})["results"][0][
                        "address"
                    ].split("/")[0]
                )
        for ip_addr in free_ip_addresses:
            # Создаем IP-адрес
            address = f"{ip_addr}/{subnet.split('/')[-1]}" 
            ip_id = create_or_get_ip_address(
                address,
                description=description,
                status="active",
            )
            # Назначаем IP интерфейсу
            assign_ip_to_interface(ip_id, device_id, interface_name)

            # Устанавливаем IP как основной для устройства
            set_primary_ip(device_id, ip_id, ip_version="ipv4")

    except Exception as e:
        logger.error(f"Failed to allocate IP to interface '{interface_name}': {e}")
        return None


def assign_ip_to_interface(ip_id, device_id, interface_name):
    """
    Связывает IP-адрес с интерфейсом устройства.
    :param ip_id: ID IP-адреса.
    :param device_id: ID устройства.
    :param interface_name: Имя интерфейса.
    """
    # Ищем интерфейс устройства
    interface_id = get_object_id(
        "dcim/interfaces", {"device_id": device_id, "name": interface_name}
    )
    if not interface_id:
        raise ValueError(
            f"Interface '{interface_name}' not found on device ID: {device_id}"
        )

    # Связываем IP с интерфейсом
    ip_address_data = api_get("ipam/ip-addresses", {"id": ip_id})
    ip_address_id = ip_address_data["results"][0]["id"]

    if not interface_id:
        raise ValueError(
            f"Interface '{interface_name}' not found on device ID: {device_id}"
        )
    ip_patch_data = {
        "assigned_object_id": interface_id,
        "assigned_object_type": "dcim.interface",
        "status": "active",
    }
    response = update_object("ipam/ip-addresses", ip_address_id, ip_patch_data)
    if response:
        logger.info(
            f"Assigned IP ID '{ip_id}' to interface '{interface_name}' (ID: {interface_id})"
        )
