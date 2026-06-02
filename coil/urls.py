from django.urls import path
from .views import *

urlpatterns = [
    path('coil_registration/', register_coil_school, name='coil_registration'),
    path('thank_you/', thank_you, name='thank_you'),
    path('coil/partner/<int:school_id>/verify/', verify_school, name='verify_school'),
    path('coil/partner/<int:school_id>/reject/', reject_school, name='reject_school'),
    path('coil_school_list/', coil_school_list, name='coil_school_list'),
    path('conference/<str:room_name>/', video_room, name='video_room'),

    path('coil/accept_invite/<uuid:token>/', accept_school_invite, name='accept_school_invite'),
    path('ask_question/', ask_question, name='ask_question'),
    path('ask_question_page/', ask_question_page, name='ask_question_page'),
    path('sdg/<int:id>/', sdg, name='sdg'),
    path('coil/partner/<int:school_id>/verify/', verify_school, name='verify_school'),
    path('sdg/certificate/<int:id>/', sdg_certificate_standalone, name='sdg_certificate_standalone'),

    # COIL student-invite flow (moved from course/urls.py).
    path('send_student_invite/<int:subject_id>/', send_student_invite, name='send_student_invite'),
    path('accept_student_invite/<uuid:token>/', accept_student_invite, name='accept_student_invite'),
]