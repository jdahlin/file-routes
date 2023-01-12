from flask import views


class View(views.View):
    def dispatch_request(self) -> str:
        return "Hello"
