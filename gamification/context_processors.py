def student_context(request):
    """Provide is_student_role, is_teacher_role, and theme_preference to all templates."""
    if not request.user.is_authenticated:
        return {"is_student_role": False, "is_teacher_role": False, "theme_preference": "dark"}

    role_name = ""
    try:
        from accounts.models import Profile
        profile = Profile.objects.select_related("role").get(user=request.user)
        if profile.role:
            role_name = profile.role_name
    except Exception:
        pass

    theme = request.COOKIES.get("theme", "dark")
    return {
        "is_student_role": role_name == "student",
        "is_teacher_role": role_name in ("teacher", "admin"),
        "theme_preference": theme,
    }
