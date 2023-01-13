## File Routes
File system based routing for Python Web Frameworks, currently supporting Django

This project has been inspired by the next.js routing.

### Background

The purpose of this project is to investigate if there's a way to make it
easier to add and write new views.

The path part of the URL was originally modelled after a unix path (/foo/bar/baz),
where each component is separated by a '/' (slash). In a web framework you typically
have one or several files that contains views. Why not combine the both?

To be able to efficiently map a url path to a filename in Python, the following
rules must be followed:

1. All routes should go in one directory, by default called `routes/`.
2. __init__.py files should be ignored in the path lookup as it
3. If you want to map the root, create a file called `index.py`, a side-effect is
   that it's not possible to create a route containing `index`

For instance:

| URL path          | Filename                  |
|-------------------|---------------------------|
| `/`               | `routes/index.py`         |
| `/home`           | `routes/home.py`          |
| `/users/`         | `routes/user/index.py`    |
| `/users/settings` | `routes/user/settings.py` |

For wildcards there are some differences between frameworks, but the general idea is:

| URL path                   | Filename                            |
|----------------------------|-------------------------------------|
| `/<str:name>`              | `routes/[str_name].py`              |
| `/<uuid:user_id>/settings` | `routes/[uuid_user_id]/settings.py` |
| `/users/`                  | `routes/user/index.py`              |
| `/users/settings`          | `routes/user/settings.py`           |


For large projects it's a good practice to write one view per file, to
avoid making it hard to find a specific view. If you follow that
you will have to duplicate the name of the view many times:

For example, in Django you would do something like this:

In `views/authenticate.py`:

```python
from django.http.request import HttpRequest
from django.http.response import HttpResponse


def authenticate(request: HttpRequest) -> HttpResponse:
    ...
    return HttpResponse(...)
```

In `urls.py`:

```python
from django.urls import path

from views.authenticate import authenticate  # noqa

urlpatterns = [
    path("authenticate", authenticate, name="authenticate")
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

Note: While not recommended, you *can* avoid duplicating some of them if you don't follow best practices,
for instance using multiple views per file, using `*` imports or avoding `reverse(...)`.

### Getting started

To use file-routes, you would currently need to use Django or Flask, support for more frameworks (e.g FastAPI) is planned.

For Django:
```
pip install file-routes[django]
```

For Flask:
```
pip install file-routes[flask]
```

That's it!

### Django Tutorial

In urls.py:

```python

from django.urls import path

from file_routes.frameworks.django import autodiscover

urlpatterns = [
 path("", autodiscover())
]


```

By default, autodiscover will scan for routes in the `routes` directory.

Create a new directory views in your django project and call it routes/authenticate.py:

```python
from django.http.request import HttpRequest
from django.http.response import HttpResponse

def view(request: HttpRequest) -> HttpResponse:
    ...
    return HttpResponse("Hello World!")
```

And that's it, you can now access this at via the URL: `/authenticate` and also via `reverse("authenticate")`

If you rename the filename to `login.py`, the url and route name will automatically update.

### Quick Video

Video script

1. Create a new project in PyCharm
2. Install via pip install
3. Add to INSTALLED_APPS
4. Create a new file
5. Access the file via a web browser

### Tests

### Tutorial

### Supported Python and Web framework versions

Currently only Django 4.1 and Python 3.11 has been tested, but it is
likely to work in older versions as well, with perhaps minimal tweaks.

### System Checks Reference

To aid users and make it easier to debug common issues, file-routes extends the [System check framework](https://docs.djangoproject.com/en/4.1/ref/checks/) in Django
and adds the following checks

* `fileroutes.W001` view must be a function
* `fileroutes.W002` view must be a class
* `fileroutes.W003` view must be a subclass of django.views.View
* `fileroutes.W004` cannot find view in module
* `fileroutes.W005` invalid view name
* `fileroutes.W006` route_kwargs must be a dict
* `fileroutes.W007` route_name must be a str

To silence one or several system checks use the [SILENCED_SYSTEM_CHECKS](https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-SILENCED_SYSTEM_CHECKS) setting.

### Settings

The default directory for the routes is called `routes`, this can be changed by adding this to your Django settings.py:

In settings.py:
```python
FILE_ROUTES_DIRECTORY = "routes"
```

## Roadmap

### MVP

This is a list of tasks that should be finished before doing the first
version and announcing

- [ ] unit tests: test errors
- [ ] document
- [ ] Error multiple views with the same name: foo.py/foo
- [ ] common decorators (csrf_enforce etc) for all views

### Future

- [ ] lazy loading?
- [ ] django: reload routes without manual restart
- [ ] Serve pretty root page with HTML docs?

## How to release

1. Bump version in `src/file_routes/__init__.py`
2. Commit and Push
3. Go to https://github.com/jdahlin/file-routes/releases/new
4. Fill in Tag (vX.Y.Z), Title and Description
5. Click on [Publish Release]
