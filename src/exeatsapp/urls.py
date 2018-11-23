from django.urls import path
from . import views

app_name = 'exeatsapp'
urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('tutor/times/', views.times, name='times'),
    path('tutor/students/', views.students, name='students'),
    path('tutor/students/<int:id>/toggle-alert', views.toggle_alert, name='toggle_alert'),
    path('tutor/times/<int:id>/toggle-attended', views.toggle_attended, name='toggle_attended'),
    path('tutor/emails/', views.emails, name='emails'),
    path('tutor/view/', views.view, name='view'),
    path('tutor/history/', views.history, name='history'),
    path('signup/<str:hash>', views.signup, name='signup'),
    path('deploy', views.deploy, name='deploy'),
]
