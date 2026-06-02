from pathlib import Path
from PIL import Image, UnidentifiedImageError  

ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_IMAGE_MB = 10 

def validate_image_file(f):
    errs = []
    if not f:
        return errs

    ctype = getattr(f, 'content_type', '') or ''
    if not ctype.startswith('image/'):
        errs.append('Invalid file type. Please upload an image (JPEG, PNG, GIF, WEBP).')
    ext = Path(getattr(f, 'name', '')).suffix.lower()
    if ext not in ALLOWED_EXTS:
        errs.append('Unsupported image type. Allowed: JPG, JPEG, PNG, GIF, WEBP.')
    if getattr(f, 'size', None) and f.size > MAX_IMAGE_MB * 1024 * 1024:
        errs.append(f'Image too large. Max size is {MAX_IMAGE_MB} MB.')
    if not errs:
        pos = f.tell() if hasattr(f, 'tell') else None
        try:
            img = Image.open(f)
            img.verify() 
        except (UnidentifiedImageError, OSError):
            errs.append('The uploaded file is not a valid image or is corrupted.')
        finally:
            try:
                if pos is not None:
                    f.seek(pos)
            except Exception:
                pass

    return errs


