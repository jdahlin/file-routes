from file_routes.route import route


@route(name="foo", default={})
def view():
    return "Hello World"
