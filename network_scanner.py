"""
DroidCommand — Network Scanner & Auto-Discovery Module
Scans the local network for Android devices with open ADB ports,
identifies hotspot gateways, and probes for CVE-2026-0073 vulnerability.
"""

import socket
import struct
import subprocess
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


# Common ADB ports: standard (5555), wireless debugging range (37000-44000)
ADB_PORTS = [5555, 5037] + list(range(37000, 37100)) + list(range(43000, 43100))
QUICK_PORTS = [5555, 5037, 37521, 37522, 37523, 43000, 43001, 43002, 43003]

# Validate an IPv4 address format
_IP_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
_SUBNET_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}$')


def get_local_ip():
    """Get the local IP address of this machine."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except Exception:
        return "127.0.0.1"
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def get_gateway_ip():
    """Get the default gateway IP (usually the hotspot host)."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1).NextHop"],
            capture_output=True, text=True, timeout=10
        )
        gw = result.stdout.strip()
        if gw and gw != "0.0.0.0" and _IP_RE.match(gw):
            return gw
    except Exception:
        pass

    # Fallback: parse ipconfig
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=10)
        matches = re.findall(r'Default Gateway.*?:\s*([\d.]+)', result.stdout)
        for m in matches:
            if m and m != "0.0.0.0" and _IP_RE.match(m):
                return m
    except Exception:
        pass

    return None


def get_subnet_prefix(ip):
    """Extract /24 subnet prefix from IP."""
    if not ip or not _IP_RE.match(ip):
        return None
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    return None


def get_arp_table(exclude_ip=None):
    """Parse ARP table for known hosts on the network."""
    hosts = []
    try:
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
        for line in result.stdout.splitlines():
            match = re.search(r'([\d.]+)\s+([\w-]+(?:[\w-]+)*)\s+(\w+)', line)
            if match:
                ip = match.group(1)
                mac = match.group(2)
                # Filter out broadcast, network, multicast, and own IP
                if not _IP_RE.match(ip):
                    continue
                octets = ip.split(".")
                last_octet = int(octets[3])
                first_octet = int(octets[0])
                if last_octet in (0, 255):
                    continue
                if 224 <= first_octet <= 239:
                    continue
                if ip == "255.255.255.255":
                    continue
                if exclude_ip and ip == exclude_ip:
                    continue
                hosts.append({"ip": ip, "mac": mac})
    except Exception:
        pass
    return hosts


def check_port(ip, port, timeout=1.5):
    """Check if a specific port is open on an IP."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        result = s.connect_ex((ip, port))
        return result == 0
    except Exception:
        return False
    finally:
        s.close()


def probe_adb_banner(ip, port, timeout=3):
    """Connect to a port and try to read an ADB banner/response."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout)
        s.connect((ip, port))

        # Send ADB CNXN packet
        banner = b"host::features=shell_v2,cmd"
        data_len = len(banner)
        csum = sum(banner) & 0xFFFFFFFF
        cmd = 0x4e584e43  # CNXN
        magic = cmd ^ 0xFFFFFFFF
        header = struct.pack("<IIIIII", cmd, 0x01000001, 256 * 1024, data_len, csum, magic)
        s.sendall(header + banner)

        # Read response header
        resp = b""
        while len(resp) < 24:
            chunk = s.recv(24 - len(resp))
            if not chunk:
                break
            resp += chunk

        if len(resp) >= 24:
            resp_cmd = struct.unpack("<I", resp[0:4])[0]
            # CNXN (0x4e584e43) or STLS (0x534c5453) or AUTH (0x41555448)
            cmd_names = {0x4e584e43: "CNXN", 0x534c5453: "STLS", 0x41555448: "AUTH"}
            cmd_name = cmd_names.get(resp_cmd, f"UNKNOWN({resp_cmd:#x})")
            return {
                "is_adb": True,
                "response": cmd_name,
                "tls_required": resp_cmd == 0x534c5453,
                "auth_required": resp_cmd == 0x41555448,
                "open_cnxn": resp_cmd == 0x4e584e43,
            }

        return {"is_adb": False}
    except Exception as e:
        return {"is_adb": False, "error": str(e)}
    finally:
        try:
            s.close()
        except Exception:
            pass


def scan_host(ip, ports=None, timeout=1.0):
    """Scan a single host for open ADB ports. Only returns confirmed ADB services."""
    if ports is None:
        ports = QUICK_PORTS

    # Deduplicate ports
    seen = set()
    unique_ports = []
    for p in ports:
        if p not in seen:
            seen.add(p)
            unique_ports.append(p)

    results = []
    for port in unique_ports:
        if check_port(ip, port, timeout=timeout):
            probe = probe_adb_banner(ip, port, timeout=3)
            if probe.get("is_adb"):
                results.append({
                    "ip": ip,
                    "port": port,
                    "open": True,
                    **probe
                })
    return results


def scan_subnet(subnet_prefix, ports=None, max_workers=50, timeout=0.8):
    """
    Scan an entire /24 subnet for open ADB ports.
    Returns list of discovered devices.
    """
    # Validate subnet format
    if not subnet_prefix or not _SUBNET_RE.match(subnet_prefix):
        return []

    if ports is None:
        ports = QUICK_PORTS

    all_results = []

    def _scan_ip(ip):
        found = []
        for port in ports:
            if check_port(ip, port, timeout=timeout):
                probe = probe_adb_banner(ip, port, timeout=3)
                if probe.get("is_adb"):
                    found.append({
                        "ip": ip,
                        "port": port,
                        **probe
                    })
        return found

    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scan_ip, ip): ip for ip in ips}
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception:
                pass

    return all_results


def full_network_recon():
    """
    Complete network reconnaissance:
    1. Get local IP & gateway
    2. Determine if connected to hotspot
    3. Scan ARP table for known hosts
    4. Probe gateway for ADB
    """
    local_ip = get_local_ip()
    gateway = get_gateway_ip()
    subnet = get_subnet_prefix(local_ip)

    # Detect hotspot pattern
    is_hotspot = False
    hotspot_info = ""
    if subnet:
        if subnet.startswith("192.168.43"):
            is_hotspot = True
            hotspot_info = "Android Hotspot standard (192.168.43.x)"
        elif subnet.startswith("192.168.49"):
            is_hotspot = True
            hotspot_info = "WiFi Direct (192.168.49.x)"
        elif subnet.startswith("172.20.10"):
            is_hotspot = True
            hotspot_info = "iPhone Hotspot (172.20.10.x)"

    # Get known hosts from ARP, excluding own IP
    arp_hosts = get_arp_table(exclude_ip=local_ip)

    # Probe gateway first (if hotspot, gateway = the phone)
    gateway_adb = None
    if gateway:
        gw_results = scan_host(gateway, ports=QUICK_PORTS, timeout=1.5)
        if gw_results:
            gateway_adb = gw_results

    return {
        "local_ip": local_ip,
        "gateway": gateway,
        "subnet": f"{subnet}.0/24" if subnet else "unknown",
        "is_hotspot": is_hotspot,
        "hotspot_type": hotspot_info,
        "arp_hosts": arp_hosts[:20],  # Cap at 20
        "gateway_adb": gateway_adb
    }
