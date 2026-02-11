from rest_framework import serializers
from django.contrib.auth import authenticate  # noqa: F401
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model - used for responses

    TODO for Interns:
    - Define the Meta class with appropriate fields
    - Decide which fields should be read-only
    - Consider what user information should be exposed via API
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'date_joined')


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration

    TODO for Interns:
    1. Add password and password_confirm fields as write_only
    2. Implement validate() method to check if passwords match
    3. Implement create() method to create user with hashed password
    4. Consider: What validations are needed? Email format? Password strength?
    """
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login

    TODO for Interns:
    1. Define email and password fields
    2. Implement validate() method to authenticate user
    3. Return the authenticated user in validated_data
    4. Handle errors: invalid credentials, inactive user
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')
        attrs['user'] = user
        return attrs
