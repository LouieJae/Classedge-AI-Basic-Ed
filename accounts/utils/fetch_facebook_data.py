import logging

from django.conf import settings
from django.core.cache import cache
from django.templatetags.static import static
import requests

logger = logging.getLogger(__name__)


def fetch_facebook_posts():
    cache_key = 'facebook_posts'
    cached_posts = cache.get(cache_key)
    if cached_posts:
        return cached_posts

    page_id = settings.FACEBOOK_PAGE_ID
    access_token = settings.FACEBOOK_ACCESS_TOKEN

    if not access_token:
        return []
    
    DEFAULT_IMAGE_URL = static('assets/img/HCCCI-logo.png')

    url = f"https://graph.facebook.com/v20.0/{page_id}/posts"
    params = {
        'access_token': access_token,
        'fields': 'message,created_time,from{id,name,picture},permalink_url,full_picture,attachments{media,subattachments}',
        'limit': 10  
    }

    try:
        response = requests.get(url, params=params, timeout=5)  
        if response.status_code == 200:
            posts = response.json().get('data', [])
            processed_posts = []

            for post in posts:
                # Try to get full_picture first (highest resolution)
                image_url = post.get('full_picture')
                
                # If no full_picture, try attachments
                if not image_url:
                    attachments = post.get('attachments', {}).get('data', [])
                    if attachments:
                        for attachment in attachments:
                            media = attachment.get('media', {})
                            if 'image' in media:
                                image_url = media['image'].get('src')
                                break
                            # Check subattachments if available
                            if 'subattachments' in attachment:
                                subattachments = attachment['subattachments'].get('data', [])
                                if subattachments and 'media' in subattachments[0]:
                                    image_url = subattachments[0]['media'].get('image', {}).get('src')
                                    break

                image_url = image_url if image_url else DEFAULT_IMAGE_URL

                message = post.get('message', '')
                first_paragraph = message.split('\n')[0] if message else 'No subject available'
                
                from_data = post.get('from', {})
                posted_by = from_data.get('name', 'Unknown')
                
                profile_picture_url = None
                if 'picture' in from_data:
                    profile_picture_url = from_data.get('picture', {}).get('data', {}).get('url')

                processed_posts.append({
                    'message': first_paragraph,
                    'created_time': post.get('created_time', ''),
                    'posted_by': posted_by,
                    'profile_picture_url': profile_picture_url,
                    'permalink_url': post.get('permalink_url', ''),
                    'image_url': image_url,
                })

            # Cache and return the processed posts
            cache.set(cache_key, processed_posts, timeout=3600)
            return processed_posts

        else:
            logger.warning("Facebook API error: %s", response.status_code)
            return []

    except requests.exceptions.RequestException:
        logger.exception("Facebook API request failed")
        return []
