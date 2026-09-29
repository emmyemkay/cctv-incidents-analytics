from django.conf import settings


def platform_metadata(request):
    return {
        "platform_version": settings.PLATFORM_VERSION,
        "deployment_environment": settings.DEPLOYMENT_ENVIRONMENT,
    }
