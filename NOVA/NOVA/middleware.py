from django.utils.deprecation import MiddlewareMixin

class DisableCacheMiddleware(MiddlewareMixin):
    """
    Middleware to aggressively prevent browser caching for all pages.
    Adds `Cache-Control: no-cache, no-store, must-revalidate` to every HTTP response.
    """
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
