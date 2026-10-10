from django.urls import path
from .views import (dashboard_page , eye_control,facial_exp 
                 , voice_control,hand_control,head_control,start_hand_control,
                stop_hand_control,video_feed ,
                hand_set_settings, hand_get_settings,
                hand_begin_calibration, hand_finish_calibration, hand_reset_calibration,
                start_head,
                stop_head,
                get_encoded_frame_head,
                start_eye, stop_eye, eye_video_feed,
                start_voice, stop_voice, voice_logs, list_microphones, execute_voice_command,
                start_facial, stop_facial, facial_logs, facial_video_feed, settings_page, reset_system, about_us)

urlpatterns = [
        path('dashboard_page/' , dashboard_page , name =  'dashboard_page'),
        path('eye_control/' , eye_control , name= 'eye_control'),
        path('facial_expression/' ,facial_exp , name= 'facial_exp'),
        # path('brain_control/' , brain_control , name='brain_control'),
        path('voice_control/' , voice_control , name='voice_control'),
        path('start_voice/' , start_voice , name='start_voice'),
        path('stop_voice/' , stop_voice , name='stop_voice'),
        path('voice_logs/' , voice_logs , name='voice_logs'),
        path('list_microphones/' , list_microphones , name='list_microphones'),
        path('execute_voice_command/' , execute_voice_command , name='execute_voice_command'),
        path('settings/' , settings_page , name='settings_page'),
        path('reset_system/' , reset_system , name='reset_system'),
        path('about_us/' , about_us , name='about_us'),


        # eye control urls
        path('start_eye/' , start_eye , name='start_eye'),
        path('stop_eye/' , stop_eye , name='stop_eye'),
        path('eye_video/' , eye_video_feed , name='eye_video_feed'),

        # facial expression urls
        path('start_facial/' , start_facial , name='start_facial'),
        path('stop_facial/' , stop_facial , name='stop_facial'),
        path('facial_logs/' , facial_logs , name='facial_logs'),
        path('facial_video/' , facial_video_feed , name='facial_video_feed'),

        # hand control urls 
        path('hand_control/' , hand_control , name='hand_control'),
        path('start/' , start_hand_control , name='start_hand'),
        path('stop/' , stop_hand_control , name='stop_hand') , 
        path('video/' , video_feed , name='video_feed'),
        path('hand_settings/' , hand_set_settings , name='hand_set_settings'),
        path('hand_get_settings/' , hand_get_settings , name='hand_get_settings'),
        path('hand_calibrate/begin/' , hand_begin_calibration , name='hand_begin_calibration'),
        path('hand_calibrate/finish/' , hand_finish_calibration , name='hand_finish_calibration'),
        path('hand_calibrate/reset/' , hand_reset_calibration , name='hand_reset_calibration'),

        # head control urls 
        path('head_control/' , head_control , name='head_control'), 
        path('start_head/',start_head , name='start_head') ,
        path('stop_head/', stop_head , name='stop_head') , 
        path('head_get_encoded_frame/',get_encoded_frame_head, name = 'head_get_encoded_frame'),
]

