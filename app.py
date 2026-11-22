import json
import urllib.request
import socket
from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import logging
import time
import os
import platform
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

VERSION = '1.3.0'

UPLOAD_FOLDER = 'uploads'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_WIDTH = 2000
MAX_IMAGE_HEIGHT = 2000

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_IMAGE_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

preview_cache = {}
CACHE_DURATION = 3600


def rate_limit(max_per_second=2):
    min_interval = 1.0 / max_per_second
    last_called = [0.0]
    def decorator(func):
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator


def extract_favicon(soup, base_url):
    favicon_selectors = [
        ('link', {'rel': 'icon'}),
        ('link', {'rel': 'shortcut icon'}),
        ('link', {'rel': 'apple-touch-icon'}),
        ('link', {'rel': 'apple-touch-icon-precomposed'})
    ]
    for tag, attrs in favicon_selectors:
        element = soup.find(tag, attrs)
        if element and element.get('href'):
            favicon_url = element['href']
            if not favicon_url.startswith(('http://', 'https://')):
                favicon_url = urljoin(base_url, favicon_url)
            return favicon_url
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"


def extract_metadata(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    title = None
    og_title = soup.find('meta', property='og:title')
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    title_tag = soup.find('title')
    if og_title and og_title.get('content'):
        title = og_title['content']
    elif twitter_title and twitter_title.get('content'):
        title = twitter_title['content']
    elif title_tag:
        title = title_tag.string
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) > 100:
            title = title[:97] + '...'
    else:
        parsed = urlparse(url)
        title = parsed.netloc
    description = None
    og_desc = soup.find('meta', property='og:description')
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if og_desc and og_desc.get('content'):
        description = og_desc['content']
    elif meta_desc and meta_desc.get('content'):
        description = meta_desc['content']
    if description:
        description = re.sub(r'\s+', ' ', description).strip()
        if len(description) > 200:
            description = description[:197] + '...'
    favicon = extract_favicon(soup, url)
    image = None
    og_image = soup.find('meta', property='og:image')
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    if og_image and og_image.get('content'):
        image = og_image['content']
    elif twitter_image and twitter_image.get('content'):
        image = twitter_image['content']
    if image and not image.startswith(('http://', 'https://')):
        image = urljoin(url, image)
    return {
        'title': title,
        'description': description,
        'favicon': favicon,
        'image': image
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/preview', methods=['POST'])
@rate_limit(max_per_second=2)
def get_preview():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL manquante'}), 400
        cache_key = url
        if cache_key in preview_cache:
            cached_data, timestamp = preview_cache[cache_key]
            if time.time() - timestamp < CACHE_DURATION:
                logger.info(f"Cache hit pour {url}")
                return jsonify(cached_data)
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return jsonify({'error': 'URL invalide'}), 400
        timeout = 10
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Tentative {attempt + 1}/{max_retries} pour {url}")
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=timeout,
                    allow_redirects=True,
                    verify=True
                )
                response.raise_for_status()
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type.lower():
                    parsed = urlparse(url)
                    result = {
                        'title': parsed.netloc,
                        'description': f"Ressource: {content_type}",
                        'favicon': f"{parsed.scheme}://{parsed.netloc}/favicon.ico",
                        'image': None,
                        'url': url
                    }
                else:
                    metadata = extract_metadata(response.text, url)
                    result = {
                        'title': metadata['title'],
                        'description': metadata['description'],
                        'favicon': metadata['favicon'],
                        'image': metadata['image'],
                        'url': url
                    }
                preview_cache[cache_key] = (result, time.time())
                return jsonify(result)
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout pour {url}, tentative {attempt + 1}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)
    except requests.exceptions.Timeout:
        logger.error(f"Timeout définitif pour {url}")
        return jsonify({
            'error': 'timeout',
            'message': 'Le site met trop de temps à répondre',
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except requests.exceptions.SSLError:
        logger.error(f"SSL error for {url}")
        return jsonify({
            'error': 'ssl_error',
            'message': 'Certificat SSL invalide',
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for {url}")
        return jsonify({
            'error': 'connection_error',
            'message': 'Impossible de se connecter au site',
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except requests.exceptions.RequestException as e:
        logger.error(f"General error for {url}: {str(e)}")
        return jsonify({
            'error': 'request_error',
            'message': str(e),
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'unknown_error',
            'message': 'Une erreur inattendue s\'est produite',
            'fallback': True,
            'title': 'Error',
            'favicon': None
        }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'MIDINS TITAN',
        'version': VERSION
    })


def compress_image(image_data, max_width=MAX_IMAGE_WIDTH, max_height=MAX_IMAGE_HEIGHT):
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.width > max_width or img.height > max_height:
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Image resized to {img.width}x{img.height}")
        buffer = io.BytesIO()
        img_format = img.format or 'PNG'
        img.save(buffer, format=img_format, optimize=True, quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8'), img_format.lower()
    except Exception as e:
        logger.error(f"Error compressing image: {str(e)}")
        return None, None


@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        filename = secure_filename(file.filename)
        if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({'error': 'Format d\'image non supporté'}), 400
        file_data = file.read()
        if len(file_data) > MAX_IMAGE_SIZE:
            return jsonify({'error': 'File exceeds maximum size'}), 400
        b64_data, img_format = compress_image(file_data)
        if not b64_data:
            return jsonify({'error': 'Erreur lors du traitement de l\'image'}), 500
        return jsonify({
            'success': True,
            'image': f'data:image/{img_format};base64,{b64_data}',
            'filename': filename
        }), 200
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/info', methods=['POST'])
def get_file_info():
    try:
        data = request.get_json()
        file_path = data.get('path')
        
        if not file_path:
            return jsonify({'error': 'Chemin de fichier manquant'}), 400
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Fichier non trouvé'}), 400
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        abs_path = os.path.abspath(file_path)
        os_name = platform.system()
        return jsonify({
            'success': True,
            'filename': file_name,
            'path': abs_path,
            'size': file_size,
            'os': os_name
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving file: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/open', methods=['POST'])
def open_file():
    try:
        data = request.get_json()
        file_path = data.get('path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Fichier non trouvé'}), 400
        abs_path = os.path.abspath(file_path)
        os_name = platform.system()
        try:
            if os_name == 'Darwin':
                os.system(f'open -R "{abs_path}"')
            elif os_name == 'Windows':
                os.system(f'explorer /select,"{abs_path}"')
            elif os_name == 'Linux':
                os.system(f'xdg-open "{os.path.dirname(abs_path)}"')
            return jsonify({'success': True}), 200
        except Exception as e:
            logger.warning(f"Impossible d'ouvrir le fichier: {str(e)}")
            return jsonify({
                'success': True,
                'message': 'Fichier ouvert (accès système limité)',
                'path': abs_path
            }), 200
    except Exception as e:
        logger.error(f"Error opening file: {str(e)}")
        return jsonify({'error': str(e)}), 500




@app.route('/api/pivot', methods=['POST'])
def execute_pivot_api():
    """
    Automated, granular, privacy-first OSINT pivot engine:
    - IP: 'geo' (Location), 'asn' (Operator / ASN), 'ptr' (Reverse PTR), 'whois' (Netblock / Org)
    - Domain: 'dns' (IPv4 A), 'dns_aaaa' (IPv6 AAAA), 'mx' (Mail Servers), 'ns' (Nameservers), 'txt' (TXT/SPF), 'subdomains' (Subdomain enumeration)
    - Email: 'email_domain' (Extract Domain), 'email_mx' (Mail Servers for Email Domain)
    - Hash: 'hash_type' (Algorithm & Bit Length Identification)
    """
    try:
        data = request.get_json() or {}
        raw_target = data.get('target', '').strip()
        pivot_type = data.get('pivot_type', 'dns').strip().lower()
        
        if not raw_target:
            return jsonify({'error': 'Target required'}), 400
            
        target = raw_target
        if '@' in target and pivot_type.startswith('email_'):
            domain_part = target.split('@')[-1].strip().lower()
        else:
            if '://' in target:
                target = urlparse(target).netloc.split(':')[0]
            else:
                target = target.split('/')[0].split(':')[0]
            target = target.strip()
            domain_part = target
        
        results = []
        
        # -----------------------------
        # IP PIVOTS
        # -----------------------------
        if pivot_type == 'geo':
            url = f'http://ip-api.com/json/{target}?fields=status,message,country,regionName,city'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res_data = json.loads(resp.read().decode())
                if res_data.get('status') == 'success':
                    loc_parts = [res_data.get('city'), res_data.get('regionName'), res_data.get('country')]
                    loc = ', '.join([p for p in loc_parts if p])
                    results.append({'value': loc, 'type': 'text', 'relation': 'location'})
                else:
                    return jsonify({'error': res_data.get('message', 'Geolocation lookup failed')}), 404
                    
        elif pivot_type == 'asn':
            url = f'http://ip-api.com/json/{target}?fields=status,message,isp,as,asname'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res_data = json.loads(resp.read().decode())
                if res_data.get('status') == 'success':
                    operator = res_data.get('as') or res_data.get('isp')
                    results.append({'value': operator, 'type': 'text', 'relation': 'operator / asn'})
                else:
                    return jsonify({'error': res_data.get('message', 'ASN lookup failed')}), 404

        elif pivot_type == 'whois':
            url = f'http://ip-api.com/json/{target}?fields=status,message,org,isp,as,asname'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res_data = json.loads(resp.read().decode())
                if res_data.get('status') == 'success':
                    org = res_data.get('org') or res_data.get('isp')
                    if org:
                        results.append({'value': org, 'type': 'text', 'relation': 'organization'})
                    as_info = res_data.get('as')
                    if as_info:
                        results.append({'value': as_info, 'type': 'text', 'relation': 'route / asn'})
                else:
                    return jsonify({'error': res_data.get('message', 'Organization lookup failed')}), 404
                    
        elif pivot_type == 'ptr':
            # Tier 1: Local socket lookup
            try:
                hostname, aliases, _ = socket.gethostbyaddr(target)
                if hostname and hostname != target:
                    results.append({'value': hostname, 'type': 'url', 'relation': 'reverse ptr'})
                    for a in aliases:
                        if a != hostname and a != target:
                            results.append({'value': a, 'type': 'url', 'relation': 'alias'})
            except Exception:
                pass

            # Tier 2: Cloudflare DoH PTR query
            if not results:
                try:
                    parts = target.split('.')
                    reversed_ip = '.'.join(reversed(parts)) + '.in-addr.arpa'
                    url = f'https://cloudflare-dns.com/dns-query?name={reversed_ip}&type=PTR'
                    req = urllib.request.Request(url, headers={'Accept': 'application/dns-json', 'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        doh_data = json.loads(resp.read().decode())
                        for ans in doh_data.get('Answer', []):
                            val = ans.get('data', '').rstrip('.')
                            if val and val != target:
                                results.append({'value': val, 'type': 'url', 'relation': 'reverse ptr'})
                except Exception:
                    pass

            # Tier 3: ip-api fallback
            if not results:
                try:
                    url = f'http://ip-api.com/json/{target}?fields=status,reverse'
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        res_data = json.loads(resp.read().decode())
                        rev = res_data.get('reverse', '').strip().rstrip('.')
                        if rev and rev != target:
                            results.append({'value': rev, 'type': 'url', 'relation': 'reverse ptr'})
                except Exception:
                    pass

            if not results:
                return jsonify({'error': 'No Reverse DNS (PTR) record found for this IP address (Reverse DNS not configured by host)'}), 404
                
        # -----------------------------
        # DOMAIN PIVOTS
        # -----------------------------
        elif pivot_type == 'dns':
            try:
                infos = socket.getaddrinfo(target, None, socket.AF_INET, socket.SOCK_STREAM)
                ips = sorted(list(set(info[4][0] for info in infos)))
                for ip in ips:
                    results.append({'value': ip, 'type': 'ip', 'relation': 'resolves to'})
            except Exception as e:
                logger.warning(f"Forward DNS failed for {target}: {e}")
                return jsonify({'error': f'IPv4 DNS resolution failed: {str(e)}'}), 404

        elif pivot_type == 'dns_aaaa':
            try:
                url = f'https://cloudflare-dns.com/dns-query?name={target}&type=AAAA'
                req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    doh_data = json.loads(resp.read().decode())
                    for ans in doh_data.get('Answer', []):
                        val = ans.get('data', '').strip()
                        if val:
                            results.append({'value': val, 'type': 'ip', 'relation': 'ipv6'})
                if not results:
                    return jsonify({'error': f'No IPv6 (AAAA) records found for {target}'}), 404
            except Exception as e:
                return jsonify({'error': f'IPv6 lookup failed: {str(e)}'}), 404
                
        elif pivot_type == 'mx':
            try:
                url = f'https://cloudflare-dns.com/dns-query?name={target}&type=MX'
                req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    doh_data = json.loads(resp.read().decode())
                    for ans in doh_data.get('Answer', []):
                        parts = ans.get('data', '').split()
                        if len(parts) >= 2:
                            results.append({'value': parts[1].rstrip('.'), 'type': 'url', 'relation': 'mail server'})
                if not results:
                    return jsonify({'error': f'No MX records found for {target}'}), 404
            except Exception as e:
                logger.warning(f"MX lookup failed for {target}: {e}")
                return jsonify({'error': f'MX lookup failed: {str(e)}'}), 404

        elif pivot_type == 'ns':
            try:
                url = f'https://cloudflare-dns.com/dns-query?name={target}&type=NS'
                req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    doh_data = json.loads(resp.read().decode())
                    for ans in doh_data.get('Answer', []):
                        val = ans.get('data', '').rstrip('.')
                        if val:
                            results.append({'value': val, 'type': 'url', 'relation': 'nameserver'})
                if not results:
                    return jsonify({'error': f'No NS records found for {target}'}), 404
            except Exception as e:
                return jsonify({'error': f'NS lookup failed: {str(e)}'}), 404

        elif pivot_type == 'txt':
            try:
                url = f'https://cloudflare-dns.com/dns-query?name={target}&type=TXT'
                req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    doh_data = json.loads(resp.read().decode())
                    for ans in doh_data.get('Answer', []):
                        val = ans.get('data', '').strip('"')
                        if val:
                            results.append({'value': val[:120], 'type': 'text', 'relation': 'txt record'})
                if not results:
                    return jsonify({'error': f'No TXT records found for {target}'}), 404
            except Exception as e:
                return jsonify({'error': f'TXT lookup failed: {str(e)}'}), 404

        elif pivot_type == 'subdomains':
            common_subs = ['www', 'api', 'mail', 'admin', 'dev', 'stage', 'vpn', 'app', 'portal', 'docs', 'status']
            for s in common_subs:
                fqdn = f'{s}.{target}'
                try:
                    socket.gethostbyname(fqdn)
                    results.append({'value': fqdn, 'type': 'url', 'relation': 'subdomain'})
                except Exception:
                    pass
            if not results:
                return jsonify({'error': f'No common subdomains resolved for {target}'}), 404

        # -----------------------------
        # EMAIL PIVOTS
        # -----------------------------
        elif pivot_type == 'email_domain':
            if domain_part and '.' in domain_part:
                results.append({'value': domain_part, 'type': 'url', 'relation': 'domain'})
            else:
                return jsonify({'error': 'Could not extract valid domain from email'}), 400

        elif pivot_type == 'email_mx':
            if not domain_part or '.' not in domain_part:
                return jsonify({'error': 'Invalid domain for email MX lookup'}), 400
            try:
                url = f'https://cloudflare-dns.com/dns-query?name={domain_part}&type=MX'
                req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    doh_data = json.loads(resp.read().decode())
                    for ans in doh_data.get('Answer', []):
                        parts = ans.get('data', '').split()
                        if len(parts) >= 2:
                            results.append({'value': parts[1].rstrip('.'), 'type': 'url', 'relation': 'mail server'})
                if not results:
                    return jsonify({'error': f'No MX records found for {domain_part}'}), 404
            except Exception as e:
                return jsonify({'error': f'Email MX lookup failed: {str(e)}'}), 404

        # -----------------------------
        # HASH PIVOTS
        # -----------------------------
        elif pivot_type == 'hash_type':
            h = raw_target.strip().lower()
            l = len(h)
            import re
            if re.match(r'^[0-9a-f]+$', h):
                if l == 32:
                    results.append({'value': 'MD5 / NTLM Hash (128-bit)', 'type': 'text', 'relation': 'algorithm'})
                elif l == 40:
                    results.append({'value': 'SHA-1 Hash (160-bit)', 'type': 'text', 'relation': 'algorithm'})
                elif l == 64:
                    results.append({'value': 'SHA-256 Hash (256-bit)', 'type': 'text', 'relation': 'algorithm'})
                elif l == 128:
                    results.append({'value': 'SHA-512 Hash (512-bit)', 'type': 'text', 'relation': 'algorithm'})
                else:
                    results.append({'value': f'Hex Digest ({l*4}-bit)', 'type': 'text', 'relation': 'format'})
            else:
                return jsonify({'error': 'Target is not a valid hexadecimal hash'}), 400
                
        return jsonify({
            'success': True,
            'source': raw_target,
            'target': target,
            'pivot_type': pivot_type,
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Pivot API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error 500: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print(f"""
    ╔═══════════════════════════════════════╗
    ║      MIDINS TITAN - OSINT TOOL        ║
    ║           Version {VERSION}              ║
    ╚═══════════════════════════════════════╝
    
    🚀 Server running at http://127.0.0.1:5000
    🔍 Case Management & Intelligence Graph
    """)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
