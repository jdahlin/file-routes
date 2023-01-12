from flask import Flask

from file_routes.frameworks.flask import FlaskFSRoutes

fsroutes = FlaskFSRoutes()
app = Flask(__name__)
app.config["FS_ROUTES_DIRECTORY"] = "routes/"
fsroutes.init_app(app)
