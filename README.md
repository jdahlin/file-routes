## django-fs-routes
File system based routing for Django

This project has been inspired by the next.js routing.

### Rationale

The purpose of this project is to investigate if there's a way to make it 
easier to add and write new viws.

For large projects it's a good practice to write one view per file, to
avoid making it hard to find a specific view. If you follow that
you will have to duplicate the name of the view many times:

Example:

In `authenticate.py`:

```python
from django.http.request import HttpRequest
from django.http.response import HttpResponse


def authentication(request: HttpRequest) -> HttpResponse:
    ...
    return HttpResponse(...)
```

In `urls.py`:

```python
from views.authenticate import authenticate


urlpatterns = [
    ...
    path("authenticate", authenticate, name="authenticate")
    ...
]
```

In the example above you end up duplicating the view name 7 times:

| #   | Description                  | Code                                  |
|-----|------------------------------|---------------------------------------|
| 1   | The filename of the view     | `authenticate.py`                     |
| 2   | The name of the view         | `def authenticate(...):`              |
| 3   | The module name in urls.py   | `from views.authenticate import ...`  |
| 4   | The function name in urls.py | `from views.... import authenticate`  |
 | 5   | The route url                | `path('authenticate', ...)`           |
| 6   | The imported view            | `path(..., authenticate, ...)`        |
| 7   | The route name               | `path(..., ..., name='authenticate')` |
---------------------------------------------------------------------------------

Note: While not recommended, you *can* avoid duplicating some of them if you don't follow best practices.

* 1: By using multiple views per file
* 5: By using `*` imports
* 7: By avoiding `reverse(...)`

With some work, you could also write a helper, so you only duplicate one time in `urls.py`.  

### Introduction

With django_fs_routes you can avoid the duplication if you want, or at your preference
only duplicate it once (filename and view name):

In urls.py:

```python
from django_fs_routes.routes import autodiscover_app_views

urlpatterns = [
    ...
    path("", autodiscover_app_views(app_name="..."))
    ...
]


```

By default django_rs_routes uses the `views` directory which will be automatically created if it does not exist.

Add this content to, views/authenticate.py:

```python
from django.http.request import HttpRequest
from django.http.response import HttpResponse

def view(request: HttpRequest) -> HttpResponse:
    ...
    return HttpResponse(...)
```

And that's it, you can now access this at via the URL: `/authenticate` and also via `reverse("authenticate")`

If you rename the filename to `login.py`, the url and route name will automatially update.

### Quick Video

Video script

1. Create a new project in PyCharm
2. Install via pip install
3. Add to INSTALLED_APPS
4. Create a new file
5. Access the file via a web browser

### Tests

### Tutorial

### Supported Python and Django versions

Currently only Django 4.1 and Python 3.11 has been tested, but it is 
likely to work in older versions as well, with perhaps minimal tweaks.

### System Checks Reference

To aid users and make it easier to debug common issues, django-fs-routes extends the [System check framework](https://docs.djangoproject.com/en/4.1/ref/checks/) in Django
and adds the following checks

* `fsroutes.W001` view must be a function
* `fsroutes.W002` view must be a class
* `fsroutes.W003` view must be a subclass of django.views.View
* `fsroutes.W004` cannot find view in module
* `fsroutes.W005` invalid view name
* `fsroutes.W006` route_kwargs must be a dict
* `fsroutes.W007` route_name must be a str

To silence one or several system checks use the [SILENCED_SYSTEM_CHECKS](https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-SILENCED_SYSTEM_CHECKS) setting.

### Settings

The default directory for views is called `views`, this can be changed by adding this to your Django settings.py:

In settings.py:
```python
DJANGO_FS_ROUTER_DIRECTORY = "fsviews"
```

## Roadmap

### MVP

This is a list of tasks that should be finished before doing the first
version and announcing

- [ ] reload routes without manual restart
- [ ] unit tests: test errors
- [ ] unit tests: class based views
- [ ] document
- [ ] use pathlib internally?
- [ ] INSTALLED_APP that automatically create the views directory
- [ ] Implement DJANGO_FS_ROUTER_DIRECTORY
- [ ] Pretty root page with HTML Docs?

### Future

Investigate this after first MVP version

- [ ] FIXME: lazy loading?
- [ ] FIXME: Flask/FastAPI support?
