import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink, db
from .auth.auth import AuthError, requires_auth
import sys
from werkzeug.exceptions import HTTPException

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


@app.route('/drinks/<int:id>', methods=['DELETE'])
@requires_auth('delete:drinks')
def delete_drink(id):
    drink = Drink.query.get(id)
    if drink is None:
        abort(404)

    error = False
    try:
        drink.delete()
    except BaseException:
        print(sys.exc_info())
        db.session.rollback()
        error = True
    finally:
        db.session.close()

    if error:
        abort(422)

    return jsonify({'success': True, 'delete': id })


## Error Handling

@app.errorhandler(Exception)
def handle_exception(error):
    """Generically munge any HTTPException as well as AuthError to jsonified
    dictionary - which in relation to the project specification include an
    extra key "name" - and munge all other errors to InternalServerError (500)
    """
    if isinstance(error, HTTPException):
        return jsonify({
            "error": error.code,
            "message": error.description,
            "name": error.name,
            "success": False
        }), error.code
    elif isinstance(error, AuthError):
        return jsonify({
            "error": error.status_code,
            "message": error.error['description'],
            "name": error.error['code'],
            "success": False
        }), error.status_code
    else:
        abort(500)
