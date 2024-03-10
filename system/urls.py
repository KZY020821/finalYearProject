from django.urls import path
from .views import views, admin_views, lecturer_views, user_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.conf.urls.i18n import i18n_patterns

urlpatterns =[
    # main
    path('', views.loginPage, name='login-page'),
    path('registerPage', views.registerPage, name='register'),
    path('logout', views.logoutUser, name='logout'),
    path('reportAttendance', views.reportAttendance, name='reportAttendance'),

    path('reset_password/', auth_views.PasswordResetView.as_view(template_name = "password_reset.html"), name='reset_password'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name = "password_reset_sent.html"), name='password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(template_name = "password_reset_form.html"), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name = "password_reset_done.html"), name='password_reset_complete'),
    

    # admin
    path('admin-dashboard', admin_views.adminDashboard, name='admin-dashboard'),

    path('admin-admin-management', admin_views.admin_adminManagement, name='admin-admin-management'),
    path('admin-create-admin', admin_views.admin_createAdmin, name='admin-create-admin'),
    path('admin-edit-admin/<int:user_id>/', admin_views.admin_editAdmin, name='admin-edit-admin'),
    path('admin-view-admin/<int:user_id>/', admin_views.admin_viewAdmin, name='admin-view-admin'),
    path('admin-remove-admin/', admin_views.admin_removeAdmin, name='admin-remove-admin'),

    path('admin-lecturer-management', admin_views.admin_lecturerManagement, name='admin-lecturer-management'),
    path('admin-create-lecturer', admin_views.admin_createLecturer, name='admin-create-lecturer'),
    path('admin-edit-lecturer/<int:user_id>/', admin_views.admin_editLecturer, name='admin-edit-lecturer'),
    path('admin-view-lecturer/<int:user_id>/', admin_views.admin_viewLecturer, name='admin-view-lecturer'),
    path('admin-remove-lecturer', admin_views.admin_removeLecturer, name='admin-remove-lecturer'),
    
    path('admin-user-management', admin_views.admin_userManagement, name='admin-user-management'),
    path('admin-create-user', admin_views.admin_createUser, name='admin-create-user'),
    path('admin-edit-user/<int:user_id>/', admin_views.admin_editUser, name='admin-edit-user'),
    path('admin-view-user/<int:user_id>/', admin_views.admin_viewUser, name='admin-view-user'),
    path('admin-remove-user', admin_views.admin_removeUser, name='admin-remove-user'),
    
    path('admin-intake-management', admin_views.admin_intakeManagement, name='admin-intake-management'),
    path('admin-create-intake', admin_views.admin_createIntake, name='admin-create-intake'),
    path('admin-edit-intake/<str:intakeCode>/', admin_views.admin_editIntake, name='admin-edit-intake'),
    path('admin-view-intake/<str:intakeCode>/', admin_views.admin_viewIntake, name='admin-view-intake'),
    path('admin-remove-intake', admin_views.admin_removeIntake, name='admin-remove-intake'),

    path('admin-subject-management', admin_views.admin_subjectManagement, name='admin-subject-management'),
    path('admin-create-subject', admin_views.admin_createSubject, name='admin-create-subject'),
    path('admin-edit-subject/<str:subjectCode>/', admin_views.admin_editSubject, name='admin-edit-subject'),
    path('admin-view-subject/<str:subjectCode>/', admin_views.admin_viewSubject, name='admin-view-subject'),
    path('admin-active-subject/<str:subjectCode>/', admin_views.admin_activeSubject, name='admin-active-subject'),
    path('admin-deactive-subject/<str:subjectCode>/', admin_views.admin_deactiveSubject, name='admin-deactive-subject'),
    path('admin-remove-subject', admin_views.admin_removeSubject, name='admin-remove-subject'),

    path('admin-class-management', admin_views.admin_classManagement, name='admin-class-management'),
    path('admin-create-class', admin_views.admin_createClass, name='admin-create-class'),
    path('admin-edit-class/<str:classCode>/', admin_views.admin_editClass, name='admin-edit-class'),
    path('admin-view-class/<str:classCode>/', admin_views.admin_viewClass, name='admin-view-class'),
    path('admin-active-class/<str:classCode>/', admin_views.admin_activeClass, name='admin-active-class'),
    path('admin-deactive-class/<str:classCode>/', admin_views.admin_deactiveClass, name='admin-deactive-class'),
    path('admin-remove-class', admin_views.admin_removeClass, name='admin-remove-class'),


    path('admin-absenceMonitoring-management', admin_views.admin_absenceMonitoringManagement, name='admin-absenceMonitoring-management'),
    path('admin-create-absenceMonitoring', admin_views.admin_createAbsenceMonitoring, name='admin-create-absenceMonitoring'),
    path('admin-edit-absenceMonitoring/<int:id>/', admin_views.admin_editAbsenceMonitoring, name='admin-edit-absenceMonitoring'),
    path('admin-view-absenceMonitoring/<int:id>/', admin_views.admin_viewAbsenceMonitoring, name='admin-view-absenceMonitoring'),
    path('admin-remove-absenceMonitoring', admin_views.admin_removeAbsenceMonitoring, name='admin-remove-absenceMonitoring'),

    path('admin-leave-management', admin_views.admin_leaveManagement, name='admin-leave-management'),
    path('admin-view-leave/<int:id>/', admin_views.admin_viewLeave, name='admin-view-leave'),
    path('admin-approve-leave/<int:id>/', admin_views.admin_approveLeave, name='admin-approve-leave'),
    path('admin-deny-leave/<int:id>/', admin_views.admin_denyLeave, name='admin-deny-leave'),
    
    path('admin-attendance-management', admin_views.admin_attendanceManagement, name='admin-attendance-management'),
    path('createCsv', admin_views.createCsv, name='createCsv'),
    path('admin-choose-subject', admin_views.admin_chooseSubject, name='admin-choose-subject'),
    path('admin-create-attendance/<str:classCode>/', admin_views.admin_createAttendance, name='admin-create-attendance'),
    path('admin-edit-attendance/<int:id>/', admin_views.admin_editAttendance, name='admin-edit-attendance'),
    path('admin-view-attendance/<int:id>/', admin_views.admin_viewAttendance, name='admin-view-attendance'),

    path('admin-report-management', admin_views.admin_reportManagement, name='admin-report-management'),
    path('admin-read-report-view/<int:id>/', admin_views.admin_readReportView, name='admin-read-report-view'),
    path('admin-read-report-reply/<int:id>/', admin_views.admin_readReportReply, name='admin-read-report-view'),
    path('admin-view-report/<int:id>/', admin_views.admin_viewReport, name='admin-view-report'),
    path('admin-reply-report/<int:id>/', admin_views.admin_replyReport, name='admin-reply-report'),
    
    path('admin-notification-management', admin_views.admin_notificationManagement, name='admin-notification-management'),
    path('admin-noted-notification/<int:id>/', admin_views.admin_notedNotification, name='admin-noted-notification'),

    path('view-myProfileAdmin/<int:user_id>/', admin_views.viewMyProfile_admin, name='view-myProfileAdmin'),

    path('admin-face/<int:user_id>/', admin_views.admin_face, name='admin-face'),
    path('admin-change-language', admin_views.admin_change_language, name='admin-change-language'),
    path('admin-import-data', admin_views.admin_import_data, name='admin-import-data'),

    # lecturer
    path('lecturer-dashboard', lecturer_views.lecturerDashboard, name='lecturer-dashboard'),

    path('lecturer-subject-management', lecturer_views.lecturer_subjectManagement, name='lecturer-subject-management'),
    path('lecturer-view-subject/<str:subjectCode>/', lecturer_views.lecturer_viewSubject, name='lecturer-view-subject'),
    
    path('lecturer-attendance-management', lecturer_views.lecturer_attendanceManagement, name='lecturer-attendance-management'),
    path('lecturer-choose-subject', lecturer_views.lecturer_chooseSubject, name='lecturer-choose-subject'),
    path('lecturer-create-attendance/<str:classCode>/', lecturer_views.lecturer_createAttendance, name='lecturer-create-attendance'),
    path('lecturer-edit-attendance/<int:id>/', lecturer_views.lecturer_editAttendance, name='lecturer-edit-attendance'),
    path('lecturer-view-attendance/<int:id>/', lecturer_views.lecturer_viewAttendance, name='lecturer-view-attendance'),

    path('view-myProfileLecturer/<int:user_id>/', lecturer_views.viewMyProfile_lecturer, name='view-myProfileLecturer'),
    path('lecturer-change-language', lecturer_views.lecturer_change_language, name='lecturer-change-language'),
    path('lecturer-face/<int:user_id>/', lecturer_views.lecturer_face, name='lecturer-face'),

    # user
    path('user-dashboard', user_views.userDashboard, name='user-dashboard'),
    
    path('user-subject-management', user_views.user_subjectManagement, name='user-subject-management'),
    path('user-view-subject/<str:classCode>/', user_views.user_viewSubject, name='user-view-subject'),
    
    path('user-absenceMonitoring-management', user_views.user_absenceMonitoringManagement, name='user-absenceMonitoring-management'),
    path('user-view-absenceMonitoring/<int:id>/', user_views.user_viewAbsenceMonitoring, name='user-view-absenceMonitoring'),

    path('user-attendance-management', user_views.user_attendanceManagement, name='user-attendance-management'),

    path('user-leave-management', user_views.user_leaveManagement, name='user-leave-management'),
    path('user-create-leave', user_views.user_createLeave, name='user-create-leave'),
    path('user-view-leave/<int:id>/', user_views.user_viewLeave, name='user-view-leave'),

    path('user-report-management', user_views.user_reportManagement, name='user-report-management'),
    path('user-create-report/<int:id>/', user_views.user_createReport, name='user-create-report'),
    path('user-view-report/<int:id>/', user_views.user_viewReport, name='user-view-report'),

    
    path('user-notification-management', user_views.user_notificationManagement, name='user-notification-management'),
    path('user-noted-notification/<int:id>/', user_views.user_notedNotification, name='user-noted-notification'),

    path('view-myProfileUser/<int:user_id>/', user_views.viewMyProfileUser, name='view-myProfileUser'),
    path('user-change-language', user_views.user_change_language, name='user-change-language'),
    # error
    path('error', views.error, name='error'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 