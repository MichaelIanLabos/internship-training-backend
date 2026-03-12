from rest_framework.views import exception_handler
from rest_framework.response import Response  # noqa: F401


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that provides consistent error responses
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'error': True,
            'status_code': response.status_code,
        }

        # Handle field errors (validation errors)
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response_data['message'] = (
                    response.data['detail']
                )
            else:
                custom_response_data['errors'] = response.data
        elif isinstance(response.data, list):
            custom_response_data['message'] = (
                response.data[0] if response.data else 'An error occurred'
            )
        else:
            custom_response_data['message'] = str(response.data)

        response.data = custom_response_data

    return response
