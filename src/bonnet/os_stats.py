#!/usr/bin/python3
import time
import platform
import psutil
import socket

def update_sys_stats():
    stats = {
        "os": get_os(),
        "os_version": get_os_version(),
        "architecture": get_architecture(),
        "processor": get_processor(),
        "network_name": get_network_name(),
        "python_version": get_python_version(),
        "cpu_usage": get_cpu_usage(),
        "ram_usage": get_ram_usage(),
        "cpu_temp": get_cpu_temp(),
        "ip_addresses": get_ip_addresses()
    }
    return stats

def get_os():
    # Get the operating system name
    return platform.system()

def get_os_version():
    # Get the operating system release version
    return platform.release()

def get_architecture():
    # Get the machine architecture
    return platform.machine()

def get_processor():
    # Get the processor name
    return platform.processor()

def get_network_name():
    # Get the network name of the computer
    return platform.node()

def get_python_version():
    # Get the Python version
    return platform.python_version()

def get_cpu_usage():
    # Get the CPU load
    return psutil.cpu_percent()

def get_ram_usage():
    # Get the RAM load
    return psutil.virtual_memory().percent

def get_cpu_temp():
    # Get the CPU temperature
    temperature_sensors = psutil.sensors_temperatures()

    return round(temperature_sensors['cpu_thermal'][0][1])

def get_ip_addresses():
    # Get all IP addresses of all interfaces
    ip_addresses = []
    for interface, addresses in psutil.net_if_addrs().items():
        for address in addresses:
            if address.family == socket.AF_INET:
                ip_addresses.append((interface, address.address))
    return ip_addresses
