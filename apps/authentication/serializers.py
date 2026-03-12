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
        # TODO: Add fields here
        # Hint: id, email, first_name, last_name, date_joined
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
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password_confirm')

    def validate(self, attrs):
        """
        TODO: Implement password matching validation
        Hint: Check if password == password_confirm
        Raise serializers.ValidationError if they don't match
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {'password': 'Passwords must match.'}
            )
        return attrs

    def create(self, validated_data):
        """
        TODO: Implement user creation
        Hint:
        - Remove password_confirm from validated_data
        - Use User.objects.create_user() to properly hash the password
        - Return the created user
        """
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


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
        """
        TODO: Implement authentication logic
        Steps:
        1. Get email and password from attrs
        2. Use authenticate() to verify credentials
        3. Check if user is active
        4. Add user to attrs['user']
        5. Return attrs

        Resources:
        - Django authenticate:
          https://docs.djangoproject.com/en/5.0/topics/auth/default/
        """
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError(
                {'password': 'Invalid credentials.'}
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                {'user': 'User account is inactive.'}
            )
        
        attrs['user'] = user
        return attrs
