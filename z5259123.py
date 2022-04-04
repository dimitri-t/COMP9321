import re
from this import d
import requests
import sqlite3
from typing import List
from flask import Flask, request
from flask_restx import Resource, Api, fields
from datetime import datetime
import urllib.parse

# ===== Constants ======
DB_NAME = 'z5259123.sqlite'
DB_TABLE_NAME = 'actors'

# ===== Flask API Connection ======
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


# ===== SQLite db functions =====

def db_connect():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def db_create_table(db):
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


def db_insert_actor(db, actor):
    shows = ', '.join([str(show) for show in actor['shows']])

    insert_actor_command = f"""INSERT INTO actors
        (name, country, birthday, deathday, gender, shows, last_updated_date)
        values ('{actor['name']}', '{actor['country']}', '{actor['birthday']}',
        '{actor['deathday']}', '{actor['gender']}', '{shows}', '{actor['last_updated_date']}')"""
    try:
        cursor = db.cursor()
        cursor.execute(insert_actor_command)
        db.commit()
        actor_id = cursor.lastrowid
        cursor.close()
        return actor_id
    except sqlite3.Error as e:
        print(f"Failed to insert actor {actor['name']}: {e}")
        return None


def db_get_actor(db, id):
    try:
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM ACTORS WHERE ID={id}")
        actor = cursor.fetchone()
        cursor.close()
        return actor
    except sqlite3.Error as e:
        print(f'Failed to find Actor {id}: {e}')
        return None


def db_delete_actor(db, id):
    try:
        cursor = db.cursor()
        cursor.execute(f"DELETE FROM ACTORS WHERE ID={id}")
        db.commit()
        cursor.close()
    except sqlite3.Error as e:
        print(f'Failed to delete Actor {id}')


def db_validate_actor_id(db, id):
    try:
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM ACTORS WHERE ID={id}")
        actor = cursor.fetchone()
        cursor.close()
        return actor != None
    except sqlite3.Error as e:
        print(f'Failed to check if Actor {id} exists: {e}')


def db_update_actor(db, id, col_name, value):
    try:
        cursor = db.cursor()
        cursor.execute(
            f"UPDATE ACTORS SET '{col_name}' = '{value}' WHERE ID={id}")
        db.commit()
        cursor.close()
    except sqlite3.Error as e:
        print(f'Failed to update Actor {id} fields {col_name} {value}: {e}')


def db_get_actors(db, order, page, size, filter):
    # Turn comma-separated string for sorting the lst
    # to an SQL statement

    order = order.split(',')
    order_sql = []
    for s in order:
        if '+' in s:
            order_type = 'ASC'
            order_keyword = s.replace('+', '')
        else:
            order_type = 'DESC'
            order_keyword = s.replace('-', '')
        order_sql.append(order_keyword + " " + order_type)

    # +name,+id will now be name ASC, id ASC
    order_sql = ','.join(order_sql)

    starting_row = (int(page) - 1) * int(size)

    try:
        sql_search_cmd = f"""SELECT {filter} FROM ACTORS
        ORDER BY {order_sql} LIMIT {starting_row}, {size}"""
        print(sql_search_cmd)
        cursor = db.cursor()
        cursor.execute(sql_search_cmd)
        result = cursor.fetchall()
        cursor.close()
        return result
    except sqlite3.Error as e:
        print(e)


def get_actor_links(db, id):
    links = {}
    links['self'] = {"href": f"http://127.0.0.1:5000/actors/{id}"}
    if db_validate_actor_id(db, id - 1):
        links['prev'] = {"href": f"http://127.0.0.1:5000/actors/{id - 1}"}
    if db_validate_actor_id(db, id + 1):
        links['next'] = {"href": f"http://127.0.0.1:5000/actors/{id + 1}"}
    return links


def get_actors_list_links(db, order, page, size, filter):
    links = {}
    links['self'] = {
        "href": f"http://127.0.0.1:5000/actors?order={order}&page={page}&size={size}&filter={filter}"}
    if db_validate_actor_id(db, (int(page) + 1) * int(size)):
        links['next'] = {
            "href": f"http://127.0.0.1:5000/actors?order={order}&page={(int(page) + 1)}&size={size}&filter={filter}"}

    if db_validate_actor_id(db, (int(page) - 1) * int(size)):
        links['prev'] = {
            "href": f"http://127.0.0.1:5000/actors?order={order}&page={(int(page) - 1)}&size={size}&filter={filter}"}

    return links


# ===== API Helpers =====
def tvmaze_handle_actor_response(data):
    actor_data = data[0]['person']
    last_updated_date = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')

    return {
        'name': actor_data['name'],
        'country': actor_data['country']['name'],
        'birthday': actor_data['birthday'],
        'deathday': actor_data['deathday'],
        'gender': actor_data['gender'],
        'last_updated_date': last_updated_date
    }, actor_data['id']


def tvmaze_create_actor_url(actor_name):
    actor_name = re.sub('[^0-9a-zA-Z]+', ' ', actor_name)
    url = 'https://api.tvmaze.com/search/people?'
    params = {'q': actor_name}
    return url + urllib.parse.urlencode(params)


def tvmaze_create_person_url(id):
    url = f'https://api.tvmaze.com/people/{id}/castcredits?'
    params = {'embed': 'show'}
    return url + urllib.parse.urlencode(params)


def tvmaze_get_actor_shows(id):
    shows = []
    url = tvmaze_create_person_url(id)

    response = requests.get(url)
    response_data = response.json()

    if response_data == None:
        return shows

    for show in response_data:
        show_name = show['_embedded']['show']['name']
        shows.append(show_name)

    return shows


def tvmaze_get_actor_info(actor_name):

    url = tvmaze_create_actor_url(actor_name)
    response = requests.get(url)
    response_data = response.json()

    actor_info, actor_tvmaze_id = tvmaze_handle_actor_response(response_data)
    actor_info['shows'] = tvmaze_get_actor_shows(actor_tvmaze_id)

    return actor_info

# ===== API HTTP Routes =====


@ api.route('/actors')
class ActorsList(Resource):
    @ api.expect(actor_input_model, validate=True)
    @ api.response(201, 'Actor Added Succesfully')
    @ api.response(400, 'Invalid actor name')
    @ api.response(404, 'Actor could not be foundß')
    def post(self):
        '''Q1 - Add a new Actor'''

        params = request.json
        if 'name' not in params or params['name'] == '':
            return {"message": "Invalid name"}, 400

        try:
            actor_info = tvmaze_get_actor_info(params['name'])
            new_actor_id = db_insert_actor(db, actor_info)
        except:
            return {"Message": f"Actor {params['name']} could not be found"}, 400

        return {
            'id': new_actor_id,
            'last-update': actor_info['last_updated_date'],
            '_links': get_actor_links(db, new_actor_id)
        }, 201

    @api.param('size', 'Number of actors per page')
    @api.param('order', 'CSV value to sort the list based on the given criteria')
    @api.param('page', 'The starting page')
    @api.param('filter', 'CSV value to specify what attributes to fetch')
    def get(self):
        '''Q5 - Retrieve the list of available actors'''
        order = request.args.get('order', '+id')
        page = request.args.get('page', 1)
        size = request.args.get('size', 10)
        filter = request.args.get('filter', 'id,name')

        actors_list = db_get_actors(db, order, page, size, filter)

        return {
            'page': page,
            'page-size': size,
            'actors': actors_list,
            '_links': get_actors_list_links(db, order, page, size, filter)
        }


@api.route('/actors/<int:id>')
@api.param('id', 'The Actor identifier')
class Actors(Resource):
    @api.response(404, 'Actor was not found')
    @api.response(200, 'Successful')
    @api.doc(description="Get an Actor by their ID")
    def get(self, id):
        '''Q2 - Get actor information'''

        if not db_validate_actor_id(db, id):
            api.abort(404, f"Actor with id {id} does not exist")

        actor = db_get_actor(db, id)

        actor_info = {
            "id": id,
            "name": actor[1],
            "country": actor[2],
            "birthday": actor[3],
            "deathday": actor[4],
            'gender': actor[5],
            "shows": actor[6].split(', '),
            "_links": get_actor_links(db, id),
            "last-update": actor[7]
        }

        return actor_info, 200

    @api.response(404, 'Actor was not found')
    @api.response(200, 'Successful')
    @api.doc(description="Delete an Actor by their ID")
    def delete(self, id):
        '''Q3 - Delete an actor'''

        if not db_validate_actor_id(db, id):
            api.abort(404, f"Actor with id {id} does not exist")

        db_delete_actor(db, id)

        return {
            "message": f"The actor with id {id} was removed from the database!",
            "id": id
        }, 200

    @api.response(200, 'Succesfull')
    @api.response(404, 'Actor was not found')
    @api.doc(body=actor_model)
    def patch(self, id):
        '''Q4 - Update an actor'''

        if not db_validate_actor_id(db, id):
            api.abort(404, f"Actor with id {id} does not exist")

        new_data = request.json
        new_updated_date = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')

        # Update each column in the actor's db entry
        # for each key-value pair in the request body
        for key, value in new_data.items():

            if type(value) == list:
                shows = ', '.join([str(s) for s in value])
                db_update_actor(db, id, key, shows)
            else:
                db_update_actor(db, id, key, value)

        db_update_actor(db, id, 'last_updated_date', new_updated_date)

        return {
            'id': id,
            'last-update': new_updated_date,
            '_links': get_actor_links(db, id)
        }


# Connecting to the database
try:
    db = db_connect()
    db_create_table(db)
except:
    print('Could not connect to database')
    exit(0)


if __name__ == '__main__':
    # Run Flask API
    app.run(debug=True)


# Close the connection
db.close()
