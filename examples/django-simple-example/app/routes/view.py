from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse


def view(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"hello": "world"})


view.route_name = "view"
view.route_kwargs = {}
