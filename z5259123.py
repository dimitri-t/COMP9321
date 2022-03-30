from dataclasses import dataclass
import json
from attr import fields, validate
from flask import Flask, request
from flask_restx import Resource, Api
from flask_restx import fields
import requests
from datetime import datetime


app = Flask(__name__)
api = Api(app)


actor_model = api.model('Actor', {
    'name': fields.String,
})


@api.route('/actors')
class ActorsList(Resource):
    @api.expect(actor_model, validate=True)
    def post(self):
        params = request.json
        if 'name' not in params or params['name'] == '':
            return {"message": "Invalid name"}, 400

        actorName = params['name']
        url = 'https://api.tvmaze.com/search/people?q=' + actorName

        # Make api request to TV Maze for actor name
        response = requests.get(url)
        actor = response.json()[0]['person']
        lastUpdatedDate = datetime.fromtimestamp(actor['updated'])
        lastUpdatedDate = lastUpdatedDate.strftime('%Y-%m-%d-%H:%M:%S')

        return {'id': actor['id'], 'last-update': lastUpdatedDate, '_links': actor['_links']}

    # {
    #     "score": 1,
    #     "person": {
    #         "id": 45790,
    #         "url": "https://www.tvmaze.com/people/45790/brad-pitt",
    #         "name": "Brad Pitt",
    #         "country": {
    #             "name": "United States",
    #             "code": "US",
    #             "timezone": "America/New_York"
    #         },
    #         "birthday": "1963-12-18",
    #         "deathday": "None",
    #         "gender": "Male",
    #         "image": {
    #             "medium": "https://static.tvmaze.com/uploads/images/medium_portrait/11/29350.jpg",
    #             "original": "https://static.tvmaze.com/uploads/images/original_untouched/11/29350.jpg"
    #         },
    #         "updated": 1589685930,
    #         "_links": {
    #             "self": {
    #                 "href": "https://api.tvmaze.com/people/45790"
    #             }
    #         }
    #     }
    # }


@api.route('/actors/<int:id>')
class Actors(Resource):
    def get(self, id):
        return {'message': id}


if __name__ == '__main__':
    app.run(debug=True)
