
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import os
import re
from django.core.files.storage import FileSystemStorage
import time
from django.contrib import messages
from accounts.models import SchoolName

# Reuse the same hex pattern the model validator enforces so client + server
# agree on what's valid.
HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

@login_required
def school_profile(request):
    if request.method == "POST" and 'logo' in request.FILES:
        logo = request.FILES['logo']

        # ✅ backend validation (content_type check)
        if logo.content_type != "image/png":
            messages.error(request, "Only PNG files are allowed.")
            return redirect('school-profile')

        filename = "HCCCI-logo.png"  # always PNG
        logo_folder = os.path.join('media', 'logos')

        os.makedirs(logo_folder, exist_ok=True)

        fs = FileSystemStorage(location=logo_folder)

        # ✅ delete any existing files in logos folder
        for existing_file in os.listdir(logo_folder):
            file_path = os.path.join(logo_folder, existing_file)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # ✅ save new file
        fs.save(filename, logo)

        messages.success(request, "School logo updated successfully!")
        return redirect('school-profile')

    school = SchoolName.objects.first()
    context = {
        "logo_update_time": int(time.time()),  # cache busting
        "school_name": school,
        # Surface the current brand color to the template so the swatches
        # can show which preset is active and the color input can pre-fill.
        "current_brand_color": (school.brand_color if school else "#1b4332").lower(),
        # 5 design-anchor presets — keep in sync with the swatches in
        # school_profile.html.
        "brand_presets": [
            {"label": "Forest",      "hex": "#1b4332"},
            {"label": "Royal Gold",  "hex": "#b7925a"},
            {"label": "Ocean",       "hex": "#0066cc"},
            {"label": "Amber",       "hex": "#c47a00"},
            {"label": "Plum",        "hex": "#7c3aed"},
        ],
    }
    return render(request, 'school_profile/school_profile.html', context)

@login_required
def change_school_name(request):
    if request.method == "POST":

        school_name = SchoolName.objects.first()

        name = request.POST.get('school_name')
        short_name = request.POST.get('school_short_name')

        if school_name:
            school_name.name = name
            school_name.short_name = short_name if short_name else None
        else:
            school_name = SchoolName.objects.create(name=name, short_name=short_name)

        school_name.save()
        messages.success(request, "School name updated successfully!")
        return redirect('school-profile')


@login_required
def change_brand_color(request):
    """Persist the tenant brand color from the school profile customizer."""
    if request.method != "POST":
        return redirect('school-profile')

    raw = (request.POST.get('brand_color') or "").strip()
    if not raw.startswith("#"):
        raw = "#" + raw

    if not HEX_COLOR_RE.match(raw):
        messages.error(request, "Invalid hex color. Use #RRGGBB or #RGB.")
        return redirect('school-profile')

    school = SchoolName.objects.first()
    if not school:
        # Edge case: brand-color change before the school name was set.
        # Persist with a placeholder so the cascade still works.
        school = SchoolName.objects.create(name="(unnamed)", short_name="")

    school.brand_color = raw.lower()
    school.save(update_fields=["brand_color"])
    messages.success(request, "Brand color updated.")
    return redirect('school-profile')