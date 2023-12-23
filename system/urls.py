from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.index, name=''),
    path('attendance', views.attendance, name='attendance'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('edit-profile', views.editProfile, name='edit-profile'),
    path('forgot-password', views.forgotPassword, name='forgot-password'),
    path('loginPage', views.loginPage, name='login'),
    path('logout', views.logoutUser, name='logout'),
    path('profile', views.profile, name='profile'),
    path('registerPage', views.registerPage, name='register'),
    path('users', views.users, name='users'),
    path('warnings', views.warnings, name='warnings'),
    path('error', views.error, name='error'),
    path('deleteUser', views.deleteUser, name='deleteUser'),
    path('registerUser', views.registerUser, name='registerUser'),
    path('registerAdmin', views.registerAdmin, name='registerAdmin'),
    path('applyLeaves', views.applyLeaves, name='applyLeaves'),
    path('reviewLeaves', views.reviewLeaves, name='reviewLeaves'),
    path('changeImage', views.changeImage, name='changeImage'),
    path('delete-user-image/', views.delete_user_image, name='delete_user_image'),
    path('test', views.test, name='test'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 