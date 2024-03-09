from import_export import resources
from .models import User, UserProfile

class UserResource(resources.ModelResource):
    class Meta:
        model = User

class UserProfileResource(resources.ModelResource):
    class Meta:
        model = UserProfile
