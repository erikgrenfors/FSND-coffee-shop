import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink, db
from .auth.auth import AuthError, requires_auth
import sys

app = Flask(__name__)
setup_db(app)
CORS(app)

'''
@TODO uncomment the following line to initialize the datbase
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! NOTE THIS MUST BE UNCOMMENTED ON FIRST RUN
'''
# db_drop_and_create_all()

## ROUTES

@app.route('/drinks', methods=['GET'])
def get_drinks():
    drinks = Drink.query.all()
    out = {
      'drinks': [drink.short() for drink in drinks],
      'success': True
    }

    return jsonify(out)


@app.route('/drinks-detail', methods=['GET'])
@requires_auth('get:drinks-detail')
def get_drinks_detail():
    drinks = Drink.query.all()
    out = {
      'drinks': [drink.long() for drink in drinks],
      'success': True
    }

    return jsonify(out)


@app.route('/drinks', methods=['POST'])
@requires_auth('post:drinks')
def create_drink():
    # print(jwt) # TODO
    body=request.get_json()

    # Ensure required body parameters (keys) are provided.
    required_keys = {'title', 'recipe'}
    if set(body) != required_keys:
        abort(400, 'Request body must include the keys: "{}"'.format(
            '", "'.join(required_keys)))

    # Munge recipe value to a list in case it is a dict.
    if isinstance(body['recipe'], dict):
        body['recipe'] = [body['recipe']]

    # Ensure required sub (recipe) parameters (keys) are provided.
    required_keys = {'color', 'name', 'parts'}
    for item in body['recipe']:
        if set(item.keys()) != required_keys:
            abort(400, 'Each recipe item must include the keys: "{}"'.format(
                '", "'.join(required_keys)))

    # Persist data in database
    drink = Drink(title=body['title'], recipe=json.dumps(body['recipe']))
    error = False
    try:
        drink.insert()
        out = {'success': True, 'drinks': [drink.long()]}
    except BaseException:
        print(sys.exc_info())
        db.session.rollback()
        error = True
    finally:
        db.session.close()

    if error:
        abort(422)

    return jsonify(out)


@app.route('/drinks/<int:id>', methods=['PATCH'])
@requires_auth('patch:drinks')
def update_drink(id):
    # Ensure only one or more of relevant body parameters (keys) are provided.
    accepted_keys = {'title', 'recipe'}
    body = request.get_json()
    invalid_params = set(body.keys()) - accepted_keys
    if len(invalid_params) != 0:
        abort(400, "Request body must not include the parameters (keys): '{}'".format(
            "', '".join(invalid_params)))

    drink = Drink.query.get(id)
    if drink is None:
        abort(404)

    # Change the drink attributes which are actually provided in body.
    for key, value in body.items():
        setattr(drink, key, value)

    # Persist data in database
    error = False
    try:
        drink.update()
        out = {'success': True, 'drinks': [drink.long()]}
    except BaseException:
        print(sys.exc_info())
        db.session.rollback()
        error = True
    finally:
        db.session.close()

    if error:
        abort(422)

    return jsonify(out)




'''
@TODO implement endpoint
    DELETE /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should delete the corresponding row for <id>
        it should require the 'delete:drinks' permission
    returns status code 200 and json {"success": True, "delete": id} where id is the id of the deleted record
        or appropriate status code indicating reason for failure
'''


## Error Handling
'''
Example error handling for unprocessable entity
'''
@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
                    "success": False, 
                    "error": 422,
                    "message": "unprocessable"
                    }), 422

'''
@TODO implement error handlers using the @app.errorhandler(error) decorator
    each error handler should return (with approprate messages):
             jsonify({
                    "success": False, 
                    "error": 404,
                    "message": "resource not found"
                    }), 404

'''

'''
@TODO implement error handler for 404
    error handler should conform to general task above 
'''


'''
@TODO implement error handler for AuthError
    error handler should conform to general task above 
'''
