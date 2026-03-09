from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.home, name="home"),
    path("analyze/", views.analyze, name="analyze"),
    path("stock/<str:ticker>/", views.stock_detail, name="stock_detail"),
]
