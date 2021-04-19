import json
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource, reqparse, abort 
from flask_jwt import JWT, jwt_required, current_identity
from manager import create_DOCUMENT_LIST_PROTOCOL, retrieve_USERS_PROTOCOL, start_FETCHING_PROTOCOL, start_aggregation_PROTOCOL, start_migration_PROTOCOL, task_report_PROTOCOL
from analyzer import Extractor
from werkzeug.security import safe_str_cmp

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
extractor = Extractor()
users = []

# ******************* JWT Authentication Setup *********************** #
class User(object):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def __str__(self):
        return "User(id='%s')" % self.id

for user, user_id in zip(retrieve_USERS_PROTOCOL().values(), retrieve_USERS_PROTOCOL()):
    users.append(User(user_id ,user['Name'],user['Email'])) 

username_table = {u.username: u for u in users}
userid_table = {u.id: u for u in users}

def authenticate(username, password):
    user = username_table.get(username, None)
    if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
        return user

def identity(payload):
    user_id = payload['identity']
    return userid_table.get(user_id, None)


app.config['JWT_SECRET_KEY'] = 'VMFqJhpkUFVUTovH0H3x210iB8Na3P1ZUusS9jOuJllmJa0EZ26GSuRds1hC'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 1200
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 1200 
jwt = JWT(app, authenticate, identity)

# ******************* Flask API Routes ******************************* #

# Test if encrypted API_Key provided is matched to uncrypted version of API_Key

class testing(Resource):

    @jwt_required()
    def get(self):
        return '%s' % current_identity

    def post(self):
        return make_response("Connection Test Successful", 200)

# ******************************************************************** #        

class Main(Resource):

    def get(self):
 
        return  jsonify(
            apiName='Flask Vision API',
            apiVersion='1.0'
            description='restful service to support android-app frontend',
            Author='Shervin Tafreshipour',
        )

# ******************************************************************** #
class Analyze(Resource):

    @jwt_required()
    def post(self):

        
        spreadsheet_ID_LIST = []
        image_ID_LIST = []
        user_id = ''
        request_DATA = request.json


        if type(request_DATA) is not None:

            for data_items in request_DATA.values():
                 spreadsheet_ID_LIST.append(data_items['spreadsheet_ID'])
                 image_ID_LIST.append(data_items['image_ID'])
                 user_id = data_items['User_ID']

        json_ID_LIST = create_DOCUMENT_LIST_PROTOCOL(user_id)
        start_FETCHING_PROTOCOL(json_ID_LIST, image_ID_LIST)
        extractor.start_EXTRACTION()
        start_aggregation_PROTOCOL(extractor.get_resultant(), request_DATA)
        start_migration_PROTOCOL()

        #return make_response(jsonify(task_report_PROTOCOL(request_DATA)),200)
        return make_response(task_report_PROTOCOL(request_DATA),200)   
            
api.add_resource(testing, '/testing')
api.add_resource(Main, '/')
api.add_resource(Analyze, '/process_images')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
