#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
MIDINS TITAN - Backend Flask
Application OSINT de Case Management avec tableau blanc interactif
"""

from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import logging
from functools import wraps
import time

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Headers réalistes pour éviter les blocages
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Cache simple pour éviter les requêtes répétées
preview_cache = {}
CACHE_DURATION = 3600  # 1 heure


def rate_limit(max_per_second=2):
    """Décorateur pour limiter le taux de requêtes"""
    min_interval = 1.0 / max_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
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
    """Extrait l'URL du favicon depuis le HTML"""
    # Chercher les différents types de favicon
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
            # Convertir en URL absolue si nécessaire
            if not favicon_url.startswith(('http://', 'https://')):
                favicon_url = urljoin(base_url, favicon_url)
            return favicon_url
    
    # Fallback: essayer /favicon.ico
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"


def extract_metadata(html, url):
    """Extrait les métadonnées d'une page web"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Titre de la page
    title = None
    
    # Ordre de priorité pour le titre
    og_title = soup.find('meta', property='og:title')
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    title_tag = soup.find('title')
    
    if og_title and og_title.get('content'):
        title = og_title['content']
    elif twitter_title and twitter_title.get('content'):
        title = twitter_title['content']
    elif title_tag:
        title = title_tag.string
    
    # Nettoyer le titre
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
        # Limiter la longueur
        if len(title) > 100:
            title = title[:97] + '...'
    else:
        # Utiliser le nom de domaine comme fallback
        parsed = urlparse(url)
        title = parsed.netloc
    
    # Description
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
    
    # Favicon
    favicon = extract_favicon(soup, url)
    
    # Image de preview
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
    """Page principale de l'application"""
    return render_template('index.html')


@app.route('/api/preview', methods=['POST'])
@rate_limit(max_per_second=2)
def get_preview():
    """
    Récupère les métadonnées d'une URL pour générer une preview
    """
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL manquante'}), 400
        
        # Vérifier le cache
        cache_key = url
        if cache_key in preview_cache:
            cached_data, timestamp = preview_cache[cache_key]
            if time.time() - timestamp < CACHE_DURATION:
                logger.info(f"Cache hit pour {url}")
                return jsonify(cached_data)
        
        # Valider l'URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return jsonify({'error': 'URL invalide'}), 400
        
        # Timeout et retry
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
                
                # Vérifier le content-type
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type.lower():
                    # Si ce n'est pas du HTML, utiliser juste le domaine
                    parsed = urlparse(url)
                    result = {
                        'title': parsed.netloc,
                        'description': f"Ressource: {content_type}",
                        'favicon': f"{parsed.scheme}://{parsed.netloc}/favicon.ico",
                        'image': None,
                        'url': url
                    }
                else:
                    # Parser le HTML
                    metadata = extract_metadata(response.text, url)
                    result = {
                        'title': metadata['title'],
                        'description': metadata['description'],
                        'favicon': metadata['favicon'],
                        'image': metadata['image'],
                        'url': url
                    }
                
                # Mettre en cache
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
        }), 200  # 200 pour permettre le fallback côté client
    
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
    """Endpoint de santé pour vérifier que le serveur fonctionne"""
    return jsonify({
        'status': 'ok',
        'service': 'MIDINS TITAN',
        'version': '1.0.0'
    })


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