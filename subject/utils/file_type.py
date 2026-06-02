import os

def get_file_type(module):
    """ Determines the file type based on extension or URL """
    
    if hasattr(module, "iframe_code") and module.iframe_code:
        return "embed"
    
    if module.url:
        url = module.url.lower()
        # Video / conferencing providers — order matters: most specific first
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        elif "teams.microsoft.com" in url or "teams.live.com" in url:
            return "msteams"
        elif "meet.google.com" in url:
            return "googlemeet"
        elif "classroom.google.com" in url:
            return "googleclassroom"
        elif "zoom.us" in url or "zoom.com" in url:
            return "zoom"
        elif "webex.com" in url:
            return "webex"
        return "url"  # Generic URL

    if module.file:
        ext = os.path.splitext(module.file.name)[1].lower()
        if ext in [".pdf"]:
            return "pdf"
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".svg"]:
            return "image"
        elif ext in [".doc", ".docx"]:
            return "word"
        elif ext in [".xls", ".xlsx"]:
            return "excel"
        elif ext in [".ppt", ".pptx"]:
            return "ppt"
        elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
            return "video"
    
    return "file"  # Default file type