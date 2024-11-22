import logging
import re

from .api_utils import create_interface

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INTERFACE_PREFIX_MAPPING = {
    "gi": "GigabitEthernet",
    "ge": "GigabitEthernet",
    "fa": "FastEthernet",
    "te": "TenGigabitEthernet",
    "et": "Ethernet",
}


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_")


def create_interface_templates(device_type_id, interface_range, interface_type):
    """
    Функция для создания интерфейсов по шаблону.
    :param device_type_id: ID типа устройства, с которым будут связаны интерфейсы.
    :param interface_range: Диапазон интерфейсов в виде строки (например, 'Gi1/0/[1-9]', 'vlan10', 'vlan[1-1200]').
    :param interface_type: Тип интерфейса (например, Ethernet, SFP, VLAN).
    """
    interfaces = []

    # Регулярное выражение для форматов Gi1/0/[1-4], Gi0/[1-9]
    interface_pattern = re.match(r"([A-Za-z]+)(\d+)(?:/(\d+))?(?:/(\d+))?/\[(\d+)-(\d+)\]", interface_range)

    # Регулярное выражение для форматов vlan10, vlan 10, vlan[1-1200], vlan [1-1200]
    vlan_pattern = re.match(r"vlan\s*\[(\d+)-(\d+)\]", interface_range, re.IGNORECASE)
    single_vlan_pattern = re.match(r"vlan\s*(\d+)", interface_range, re.IGNORECASE)

    if interface_pattern:
        # Обработка диапазонов Gi1/0/[1-4] и аналогичных
        interface_prefix, unit, module, port, start_range, end_range = interface_pattern.groups()
        for number in range(int(start_range), int(end_range) + 1):
            if module and port:
                interfaces.append(f"{interface_prefix}{unit}/{module}/{port}/{number}")
            elif module:
                interfaces.append(f"{interface_prefix}{unit}/{module}/{number}")
            else:
                interfaces.append(f"{interface_prefix}{unit}/{number}")

    elif vlan_pattern:
        # Обработка диапазонов VLAN
        start_vlan, end_vlan = map(int, vlan_pattern.groups())
        if start_vlan > end_vlan or start_vlan < 1 or end_vlan > 4094:
            raise ValueError(f"Invalid VLAN range: {start_vlan}-{end_vlan}. VLANs must be between 1 and 4094.")
        for vlan_id in range(start_vlan, end_vlan + 1):
            interfaces.append(f"vlan{vlan_id}")

    elif single_vlan_pattern:
        # Обработка одного VLAN
        vlan_id = int(single_vlan_pattern.group(1))
        if vlan_id < 1 or vlan_id > 4094:
            raise ValueError(f"Invalid VLAN ID: {vlan_id}. VLANs must be between 1 and 4094.")
        interfaces.append(f"vlan{vlan_id}")

    else:
        # Если формат не распознан, выбрасываем исключение
        raise ValueError(
            f"Invalid interface range format: {interface_range}. "
            f"Expected formats: 'Gi1/0/[1-4]', 'vlan10', 'vlan [1-1200]', etc."
        )

    # Создание интерфейсов с нормализованными именами
    for interface_name in interfaces:
        normalized_name = normalize_interface_name(interface_name)
        create_interface(normalized_name, interface_type, device_type_id)


def normalize_interface_name(interface_name):
    """
    Нормализует имя интерфейса, заменяя префиксы на нужные из мапинга.
    :param interface_name: Имя интерфейса (например, 'Gi1/0/1').
    :return: Нормализованное имя интерфейса (например, 'GigabitEthernet1/0/1').
    """
    # Извлекаем префикс из имени интерфейса
    match = re.match(r"([a-zA-Z]+)(.*)", interface_name)
    if not match:
        raise ValueError(f"Invalid interface name format: {interface_name}")
    
    prefix, rest = match.groups()
    normalized_prefix = INTERFACE_PREFIX_MAPPING.get(prefix.lower(), prefix)  # Приводим к нижнему регистру и заменяем
    return f"{normalized_prefix}{rest}"
