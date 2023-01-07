from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse

route_name = __name__
route_kwargs = {}
route_framework = "django" | "django-ninja" | "starlette" | "flask" | "falcon"


def view(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"hello": "world"})


# ------

# django-ninja
class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


def get() -> dict[str, str]:
    return {"hello": "world"}


def post(item: Item) -> Item:
    return item
