from utils.object_utils import (allocate_ip_to_device_interface, create_device,
                                create_or_get_device_role,
                                create_or_get_device_type,
                                create_or_get_manufacturer,
                                create_or_get_prefix, create_or_get_site,
                                find_available_device_name)


def create_site(site_name, manufacturer_name, devices, prefix):
    site_id = create_or_get_site(site_name)
    manufacturer_id = create_or_get_manufacturer(manufacturer_name)
    create_or_get_prefix(prefix)
    # Итерируемся по devices и разбираем на подзадачи все составляющие
    for device in devices:
        interfaces = device.get("interfaces")
        subnet = device.get("subnet")
        # создаем device_type
        device_type_id = create_or_get_device_type(
            manufacturer_id, device["model"], interfaces
        )
        # Создаем device_role 
        role_id = create_or_get_device_role(device["role"], device["role_color"])
        # Собираем device name на основе suffix в ямле вида {site_name}-{suffix}-{index:02d}
        device_names = find_available_device_name(
            site_name, device["name_suffix"], device["count"]
        )

        for device_name in device_names:
            # Создаем устройство
            device_id = create_device(device_name, device_type_id, role_id, site_id)
            if device_id and subnet:
                # Назначаем IP для всех виртуальных интерфейсов
                for iface in interfaces:
                    if iface["interface_type"] == "virtual" and iface["primary"] == True:
                        allocate_ip_to_device_interface(
                            device_id,
                            iface["interface_range"],
                            subnet,
                            device=device_name,
                            description=device_name,
                            count=device["count"],
                        )
