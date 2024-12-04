from flask import Flask
from backends.models import db



app =None

def create_app():
    app = Flask(__name__)
    app.debug =True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///Insponsor1.sqlite3"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = "False"
    app.config ['SECRET_KEY']= "123432167436"
    app.config['UPLOAD_FOLDER'] = 'static/img/profile_pics'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    db.init_app(app)
    app.app_context().push()
    return app




app = create_app()


#db.drop_all()
db.create_all()



from backends.controllers import *


if __name__ =="__main__":
    app.run()