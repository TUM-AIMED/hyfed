"""
    JWT token configuration

    Copyright 2021 Julian Matschinske. All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


def jwt_token_middleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):

        # Code to be executed for each request before
        # the view (and later middleware) are called.

        if not request.META.get('HTTP_AUTHORIZATION') and \
                not request.GET.get('token') and \
                not request.GET.get('noauth'):
            cookie_access_token = request.COOKIES.get("access_token")
            query_access_token = request.GET.get("access_token")

            access_token = query_access_token if query_access_token else cookie_access_token

            if access_token:
                request.META['HTTP_AUTHORIZATION'] = f"Bearer {access_token}"

        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
