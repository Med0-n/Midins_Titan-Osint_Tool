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
                logger.warning(f"Erreur requête pour {url}: {str(e)}")
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
        logger.error(f"Erreur SSL pour {url}")
        return jsonify({
            'error': 'ssl_error',
            'message': 'Certificat SSL invalide',
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except requests.exceptions.ConnectionError:
        logger.error(f"Erreur de connexion pour {url}")
        return jsonify({
            'error': 'connection_error',
            'message': 'Impossible de se connecter au site',
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur générale pour {url}: {str(e)}")
        return jsonify({
            'error': 'request_error',
            'message': str(e),
            'fallback': True,
            'title': urlparse(url).netloc if url else 'URL',
            'favicon': None
        }), 200
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return jsonify({
            'error': 'unknown_error',
            'message': 'Une erreur inattendue s\'est produite',
            'fallback': True,
            'title': 'Erreur',
            'favicon': None
        }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'MIDINS TITAN',
        'version': '1.0.0'
    })


def compress_image(image_data, max_width=MAX_IMAGE_WIDTH, max_height=MAX_IMAGE_HEIGHT):
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.width > max_width or img.height > max_height:
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Image redimensionnée de {img.width}x{img.height}")
        buffer = io.BytesIO()
        img_format = img.format or 'PNG'
        img.save(buffer, format=img_format, optimize=True, quality=85)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8'), img_format.lower()
    except Exception as e:
        logger.error(f"Erreur lors de la compression d'image: {str(e)}")
        return None, None


@app.route('/api/upload/image', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        filename = secure_filename(file.filename)
        if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({'error': 'Format d\'image non supporté'}), 400
        file_data = file.read()
        if len(file_data) > MAX_IMAGE_SIZE:
            return jsonify({'error': 'Fichier trop volumineux'}), 400
        b64_data, img_format = compress_image(file_data)
        if not b64_data:
            return jsonify({'error': 'Erreur lors du traitement de l\'image'}), 500
        return jsonify({
            'success': True,
            'image': f'data:image/{img_format};base64,{b64_data}',
            'filename': filename
        }), 200
    except Exception as e:
        logger.error(f"Erreur lors de l'upload d'image: {str(e)}")
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
        logger.error(f"Erreur lors de la récupération du fichier: {str(e)}")
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
        logger.error(f"Erreur lors de l'ouverture du fichier: {str(e)}")
        return jsonify({'error': str(e)}), 500



@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erreur serveur 500: {str(error)}")
    return jsonify({'error': 'Erreur interne du serveur'}), 500


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════╗
    ║      MIDINS TITAN - OSINT TOOL        ║
    ║            Version 1.0.0              ║
    ╚═══════════════════════════════════════╝
    
    🚀 Serveur démarré sur http://127.0.0.1:5000
    🔍 Case Management & Intelligence Graph
    """)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
