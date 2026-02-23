#!/usr/bin/env python3
"""
Download a free game from itch.io.

Handles itch.io's download mechanism for free games by:
1. Fetching the game page to extract CSRF token and upload IDs
2. Identifying the correct platform upload (Linux)
3. POSTing to get a signed CDN download URL
4. Downloading the file with progress reporting

Usage:
    python3 -m mados_meli_demo.download_itch <game_url> <platform> <output_path>

Example:
    python3 -m mados_meli_demo.download_itch \\
        https://williamsmygl.itch.io/meli-a-tech-demo-by-williamsmygl \\
        Linux /tmp/meli-demo.zip
"""

import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Timeout for HTTP requests (seconds)
HTTP_TIMEOUT = 30
# User agent to use for requests
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


def _create_opener():
    """Create a urllib opener with cookie support."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPRedirectHandler(),
    )
    opener.addheaders = [("User-Agent", USER_AGENT)]
    return opener


def _fetch_page(opener, url):
    """Fetch a page and return its HTML content."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _extract_csrf_token(html):
    """Extract CSRF token from itch.io page HTML."""
    # Try meta tag first
    match = re.search(
        r'<meta\s+name="csrf_token"\s+(?:value|content)="([^"]+)"', html
    )
    if match:
        return match.group(1)

    # Try JS variable
    match = re.search(r"I\.XsrfToken\s*=\s*[\"']([^\"']+)[\"']", html)
    if match:
        return match.group(1)

    # Try hidden input form field
    match = re.search(
        r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"', html
    )
    if match:
        return match.group(1)

    return None


def _extract_uploads(html, platform_keyword):
    """
    Extract upload IDs from itch.io page HTML.
    Returns list of (upload_id, name) tuples matching the platform.
    """
    results = []

    # Strategy 1: Find upload_id attributes with nearby platform text
    # itch.io HTML structure: <div class="upload" data-upload_id="XXXXX">
    #   ... <strong class="name">Game Name | For Linux</strong> ...
    upload_sections = re.finditer(
        r'data-upload_id="(\d+)"', html
    )

    for match in upload_sections:
        uid = match.group(1)
        # Look at surrounding context (500 chars before and after)
        start = max(0, match.start() - 200)
        end = min(len(html), match.end() + 800)
        context = html[start:end]

        if platform_keyword.lower() in context.lower():
            # Try to extract the upload name
            name_match = re.search(
                r'class="[^"]*name[^"]*"[^>]*>([^<]+)', context
            )
            name = name_match.group(1).strip() if name_match else f"Upload {uid}"

            # Avoid duplicates
            if uid not in [r[0] for r in results]:
                results.append((uid, name))

    # Strategy 2: Look for JSON data embedded in the page
    if not results:
        json_match = re.search(
            r'data-uploads_url="([^"]+)"', html
        )
        if json_match:
            # There's a URL to fetch uploads from
            pass  # We'll handle this in the main flow

    return results


def _get_download_url(opener, game_url, upload_id, csrf_token):
    """
    Get the actual download URL for an upload.

    For free games, POST to <game_url>/file/<upload_id> with CSRF token
    to get a JSON response with the CDN URL.
    """
    file_url = f"{game_url}/file/{upload_id}"

    # Try POST with CSRF token (standard itch.io method)
    if csrf_token:
        data = urllib.parse.urlencode({
            "csrf_token": csrf_token,
            "source": "game_download",
        }).encode("utf-8")

        req = urllib.request.Request(
            file_url,
            data=data,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": game_url,
            },
        )

        try:
            with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
                resp_body = resp.read().decode("utf-8", errors="replace")

                # Try JSON response: {"url": "https://..."}
                try:
                    json_data = json.loads(resp_body)
                    url = json_data.get("url")
                    if url:
                        return url
                except (json.JSONDecodeError, ValueError):
                    pass

                # Try HTML with redirect URL
                url_match = re.search(
                    r'(https://[^\s"\'<>]+\.zip[^\s"\'<>]*)', resp_body
                )
                if url_match:
                    return url_match.group(1)

                # Try meta refresh
                refresh_match = re.search(
                    r'url=(https://[^\s"\'<>]+)', resp_body, re.IGNORECASE
                )
                if refresh_match:
                    return refresh_match.group(1)

        except urllib.error.HTTPError:
            pass

    # Fallback: Try GET with query parameter (some free games)
    try:
        get_url = f"{file_url}?source=game_download"
        req = urllib.request.Request(
            get_url,
            headers={"User-Agent": USER_AGENT, "Referer": game_url},
        )
        with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
            # The final URL after redirects might be the CDN URL
            final_url = resp.url
            if "itch.zone" in final_url or "itch-skins" in final_url:
                return final_url

            resp_body = resp.read().decode("utf-8", errors="replace")
            try:
                json_data = json.loads(resp_body)
                url = json_data.get("url")
                if url:
                    return url
            except (json.JSONDecodeError, ValueError):
                pass

    except urllib.error.HTTPError:
        pass

    return None


def _progress_hook(block_count, block_size, total_size):
    """Display download progress."""
    downloaded = block_count * block_size
    if total_size > 0:
        percent = min(100.0, downloaded * 100.0 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        bar_len = 30
        filled = int(bar_len * percent / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        sys.stdout.write(
            f"\r  [{bar}] {percent:.1f}% ({mb_down:.1f}/{mb_total:.1f} MB)"
        )
    else:
        mb_down = downloaded / (1024 * 1024)
        sys.stdout.write(f"\r  Descargado: {mb_down:.1f} MB")
    sys.stdout.flush()


def download_from_itch(game_url, platform_keyword, output_path):
    """
    Download a game from itch.io.

    Args:
        game_url: Full URL to the itch.io game page
        platform_keyword: Platform to download (e.g., "Linux", "Windows")
        output_path: Path to save the downloaded file

    Returns:
        True if download succeeded, False otherwise
    """
    opener = _create_opener()

    # Step 1: Fetch the game page
    print(f"  Accediendo a itch.io...")
    try:
        html = _fetch_page(opener, game_url)
    except (urllib.error.URLError, OSError) as e:
        print(f"  Error al acceder a la página: {e}")
        return False

    # Step 2: Extract CSRF token
    csrf_token = _extract_csrf_token(html)
    if not csrf_token:
        print("  Advertencia: No se encontró CSRF token (continuando...)")

    # Step 3: Find platform-specific uploads
    uploads = _extract_uploads(html, platform_keyword)

    if not uploads:
        print(f"  Error: No se encontraron descargas para '{platform_keyword}'")
        print("  Descargas disponibles en la página pueden requerir descarga manual.")
        return False

    # Use the first matching upload
    upload_id, upload_name = uploads[0]
    print(f"  Encontrado: {upload_name} (ID: {upload_id})")

    # Step 4: Get the download URL
    print("  Obteniendo URL de descarga...")
    cdn_url = _get_download_url(opener, game_url, upload_id, csrf_token)

    if not cdn_url:
        print("  Error: No se pudo obtener la URL de descarga.")
        print(f"  Descarga manual: {game_url}")
        return False

    # Step 5: Download the file
    print(f"  Descargando {platform_keyword} build...")
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        urllib.request.urlretrieve(cdn_url, output_path, _progress_hook)
        print("")  # Newline after progress bar

        # Verify the file was downloaded
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  ✓ Descarga completada ({size_mb:.1f} MB)")
            return True
        else:
            print("  Error: El archivo no se guardó correctamente")
            return False

    except (urllib.error.URLError, OSError) as e:
        print(f"\n  Error durante la descarga: {e}")
        # Clean up partial download
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def main():
    """CLI entry point."""
    if len(sys.argv) != 4:
        print(f"Uso: {sys.argv[0]} <game_url> <platform> <output_path>")
        print(f"Ejemplo: {sys.argv[0]} https://user.itch.io/game Linux /tmp/game.zip")
        sys.exit(1)

    game_url = sys.argv[1]
    platform = sys.argv[2]
    output_path = sys.argv[3]

    success = download_from_itch(game_url, platform, output_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
