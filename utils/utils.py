import logging
import re

from .api_utils import create_interface

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_")


def create_interface_templates(device_type_id, interface_range, interface_type):
    """
    Функция для создания интерфейсов по шаблону.
    :param device_type_id: ID типа устройства, с которым будут связаны интерфейсы.
    :param interface_range: Диапазон интерфейсов в виде строки (например, 'Gi1/0/[1-9]').
    """
    # Разбираем диапазон интерфейсов с помощью регулярного выражения
    if "/" in interface_range:
        pattern = re.match(r"([A-Za-z]+)(\d+)/(\d+)/\[(\d+)-(\d+)\]", interface_range)

        if not pattern:
            raise ValueError(
                "Invalid interface range format. Use: <interface_name><unit>/<module>/<port>, e.g., Gi1/0/[1-9]"
            )

        interface_prefix, unit, module, start_port, end_port = pattern.groups()

        # Генерируем список интерфейсов
        interfaces = []
        for port in range(int(start_port), int(end_port) + 1):
            interface_name = f"{interface_prefix}{unit}/{module}/{port}"
            interfaces.append(interface_name)

        # Создаем интерфейсы через API
        for interface_name in interfaces:
            create_interface(interface_name, interface_type, device_type_id)

    else:
        interface_name = interface_range
        create_interface(interface_name, interface_type, device_type_id)
