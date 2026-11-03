"""Safe HTTP client with strict SSRF protection, timeout, and redirect validation."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
import httpx

# Disallowed private and special-purpose IP networks
DISALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class SSRFValidationError(ValueError):
    """Raised when a URL resolves to a prohibited local or private address."""
    pass


def validate_url_safe(url: str) -> str:
    """Validates that a URL uses http/https and resolves exclusively to public IP addresses."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFValidationError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL lacks a valid hostname.")

    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise SSRFValidationError(f"Access to loopback target '{hostname}' is blocked.")

    # 1. Direct IP check (covers IP literals like 192.168.1.1, 10.0.0.1)
    is_ip = False
    try:
        ip_direct = ipaddress.ip_address(hostname)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip:
        for net in DISALLOWED_NETWORKS:
            if ip_direct in net:
                raise SSRFValidationError(
                    f"Target host '{hostname}' is a private/internal IP {ip_direct}, which is prohibited."
                )
        return url.strip()

    # 2. Resolve DNS hostname to IP addresses
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve hostname '{hostname}': {e}")

    for family, _, _, _, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        for net in DISALLOWED_NETWORKS:
            if ip_obj in net:
                raise SSRFValidationError(
                    f"Target host '{hostname}' resolves to private/internal IP {ip_str}, which is prohibited."
                )

    return url.strip()


def safe_fetch(url: str, timeout_seconds: float = 8.0, max_bytes: int = 2_000_000) -> str:
    """Fetches web content with SSRF checks on initial URL and all subsequent redirect targets."""
    current_url = validate_url_safe(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (KorvarcOS/1.0; Research)",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    max_redirects = 4
    redirect_count = 0

    with httpx.Client(timeout=timeout_seconds, follow_redirects=False, headers=headers) as client:
        while redirect_count <= max_redirects:
            validate_url_safe(current_url)
            response = client.get(current_url)

            if response.is_redirect:
                redirect_url = response.headers.get("Location")
                if not redirect_url:
                    raise ValueError("Redirect response received with no Location header.")
                from urllib.parse import urljoin
                current_url = urljoin(current_url, redirect_url)
                redirect_count += 1
                continue

            response.raise_for_status()
            content = response.content[:max_bytes]
            return content.decode("utf-8", errors="replace")

        raise ValueError(f"Exceeded maximum redirects ({max_redirects}) for URL: {url}")
