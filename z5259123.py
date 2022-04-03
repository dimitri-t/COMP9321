import re
import requests
import sqlite3
from typing import List
from flask import Flask, request
from flask_restx import Resource, Api, fields
from datetime import datetime

app = Flask(__name__)
api = Api(app)

# ===== Flask rest plus models =====
actor_input_model = api.model('New actor input', {
    'name': fields.String,
})

actor_model = api.model('Actor', {
    'name': fields.String,
    'country': fields.String,
    'birthday': fields.String,
    'deathday': fields.String,
    'gender': fields.String,
    'shows': fields.List(fields.String),
})


# ===== SQLite functions =====

def create_table(db):
    create_table_sql_command = """CREATE TABLE IF NOT EXISTS actors(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        country TEXT,
        birthday TEXT,
        deathday TEXT,
        gender TEXT,
        shows TEXT,
        last_updated_date TEXT NOT NULL)
    """
    try:
        cursor = db.cursor()
        cursor.execute(create_table_sql_command)
        db.commit()
        cursor.close()
    except sqlite3.Error as e:
        print(f'Failed to create table" {e}')


def insert_actor(db, name, country, birthday, deathday, gender, shows, last_updated_date):
    insert_actor_command = f"""INSERT INTO actors
        (name, country, birthday, deathday, gender, shows, last_updated_date)
        values ('{name}', '{country}', '{birthday}',
        '{deathday}', '{gender}', '{shows}', '{last_updated_date}')"""
    try:
        cursor = db.cursor()
        cursor.execute(insert_actor_command)
        db.commit()
        actor_id = cursor.lastrowid
        cursor.close()
        return actor_id
    except sqlite3.Error as e:
        print(f'Failed to insert actor {name}: {e}')
        return None


def get_actor(db, id):
    try:
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM ACTORS WHERE ID={id}")
        actor = cursor.fetchone()
        cursor.close()
        return actor
    except sqlite3.Error as e:
        print(f'Failed to find Actor {id}: {e}')
        return None


def delete_actor(db, id):
    try:
        cursor = db.cursor()
        cursor.execute(f"DELETE FROM ACTORS WHERE ID={id}")
        db.commit()
        cursor.close()
    except sqlite3.Error as e:
        print(f'Failed to delete Actor {id}')


def validate_actor_id(db, id):
    try:
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM ACTORS WHERE ID={id}")
        actor = cursor.fetchone()
        cursor.close()
        return actor != None
    except sqlite3.Error as e:
        print(f'Failed to check if Actor {id} exists: {e}')


def update_actor(db, id, col_name, value):
    try:
        cursor = db.cursor()
        cursor.execute(
            f"UPDATE ACTORS SET '{col_name}' = '{value}' WHERE ID={id}")
        db.commit()
        cursor.close()
    except sqlite3.Error as e:
        print(f'Failed to update Actor {id} fields {col_name} {value}: {e}')


def get_actor_links(db, id):
    return {
        'self': {
            "href": f"http://127.0.0.1:5000/actors/{id}"
        }
    }


# Connecting to the database
db_name = 'z5259123.sqlite'
table_name = 'actors'
db = sqlite3.connect(db_name, check_same_thread=False)
create_table(db)


# ===== API HTTP Routes =====

@api.route('/actors')
class ActorsList(Resource):
    @api.expect(actor_input_model, validate=True)
    @api.response(201, 'Actor Added Succesfully')
    @api.response(400, 'Invalid actor name')
    def post(self):
        '''Q1 - Add a new Actor'''

        params = request.json
        if 'name' not in params or params['name'] == '':
            return {"message": "Invalid name"}, 400

        actor_name = re.sub('[^0-9a-zA-Z]+', ' ', params['name'])

        url = 'https://api.tvmaze.com/search/people?q=' + actor_name

        response = requests.get(url)
        response_data = response.json()

        if not response_data:
            return {"Message": f"Actor {actor_name} could not be found"}, 400

        actor_info = response_data[0]['person']
        last_updated_date = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
        shows = ''

        new_actor_id = insert_actor(db,
                                    actor_info['name'],
                                    actor_info['country']['name'],
                                    actor_info['birthday'],
                                    actor_info['deathday'],
                                    actor_info['gender'],
                                    shows,
                                    last_updated_date)

        return {
            'id': new_actor_id,
            'last-update': last_updated_date,
            '_links': get_actor_links(db, new_actor_id)
        }, 201


@api.route('/actors/<int:id>')
@api.param('id', 'The Actor identifier')
class Actors(Resource):
    @api.response(404, 'Actor was not found')
    @api.response(200, 'Successful')
    @api.doc(description="Get an Actor by their ID")
    def get(self, id):
        '''Q2 - Get actor information'''

        if not validate_actor_id(db, id):
            api.abort(404, f"Actor with id {id} does not exist")

        actor = get_actor(db, id)

        actor_info = {
            "id": id,
            "name": actor[1],
            "country": actor[2],
            "birthday": actor[3],
            "deathday": actor[4],
            'gender': actor[5],
            "shows": actor[6],
            "_links": get_actor_links(db, id),
            "last-update": actor[7]
        }

        return actor_info, 200

    @api.response(404, 'Actor was not found')
    @api.response(200, 'Successful')
    @api.doc(description="Delete an Actor by their ID")
    def delete(self, id):
        '''Q3 - Delete an actor'''

        if not validate_actor_id(db, id):
            api.abort(404, f"Actor with id {id} does not exist")

        delete_actor(db, id)

        return {
            "message": f"The actor with id {id} was removed from the database!",
            "id": id
        }, 200

    @api.response(200, 'Succesfull')
    @api.response(404, 'Actor was not found')
    @api.doc(body=actor_model)
    def patch(self, id):
        '''Q4 - Update an actor'''

        if not validate_actor_id(db, id):
            api.abort(404, f"Actor with id {id} does not exist")

        new_data = request.json
        new_updated_date = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')

        # Update each column in the actor's db entry
        # for each key-value pair in the request body
        for key, value in new_data.items():

            # ! Handle the list of shows part !
            if type(value) != List:
                update_actor(db, id, key, value)

        update_actor(db, id, 'last_updated_date', new_updated_date)

        return {
            'id': id,
            'last-update': new_updated_date,
            '_links': get_actor_links(db, id)
        }


if __name__ == '__main__':
    app.run(debug=True)

# Close the connection
db.close()
