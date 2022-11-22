from flask import jsonify
from api.util import *
from flask_restful import Resource, request
from datetime import datetime
import requests
import yaml
import simplejson as json

class Login(Resource):
    def post(self):

        args = request.get_json(force=True)

        #do nothing if double login bc hackathon
        exec_commit('INSERT INTO Users (username, avatar) VALUES (%s, %s) ON CONFLICT DO NOTHING', [args['username'], args['avatar']])

        return jsonify(success=True)

class Friends(Resource):

    #get all friends on map load
    def get(self):
        arr = []
        db_resp = exec_get_all('SELECT Friends.friend, Users.currentSongName, Users.currentSongGenre, ' 
                               'Users.currentSongArtist, Users.currentSongId, Users.currentLat, Users.currentLong, Users.avatar FROM ' 
                               '(Users LEFT JOIN Friends ON Friends.friend = Users.username) ' 
                               'WHERE Friends.curUser = %s', [request.args.get('username')])

        for user in db_resp:
            arr.append({"name": user[0],
                        "avatar": user[7],
                 "song": {
                    "name": user[1],
                    "artist": user[3],
                    "genre": user[2],
                    "id": user[4]
                 },
                "location": {
                    'latitude': str(user[5]),
                    'longitude': str(user[6]),
                }
            })

        return arr

    #add a friend
    def post(self):
        args = request.get_json(force=True)

        #add first direction of friendship
        exec_commit('INSERT INTO Friends (curUser, friend) VALUES (%s, %s) RETURNING friend',
                               [args['username'], args['friend']])
        #add second direction of friendship
        exec_commit('INSERT INTO Friends(curUser, friend) VALUES (%s, %s)', [args['friend'], args['username']])


        return jsonify(success=True)


class FriendAccept(Resource):
    def post(self):
        args = request.get_json(force=True)

        #print(args['friend'], args['username'])
        #remove the request
        exec_commit('DELETE FROM FriendRequests WHERE sender=%s AND receiver=%s',[args['friend'], args['username']])

        #add the bi-directional friendship to the friends table
        exec_commit('INSERT INTO Friends(curUser, friend) VALUES (%s, %s) ON CONFLICT DO NOTHING', [args['username'], args['friend']])

        exec_commit('INSERT INTO Friends(curUser, friend) VALUES (%s, %s) ON CONFLICT DO NOTHING', [args['friend'], args['username']])

        return jsonify(success=True)


class FriendDeny(Resource):
    def post(self):
        args = request.get_json(force=True)

        #remove the request
        exec_commit('DELETE FROM FriendRequests WHERE sender=%s AND receiver=%s',[args['friend'], args['username']])

        return jsonify(success=True)

class FriendRequest(Resource):
    def get(self):

        arr = []

        db_resp = exec_get_all('SELECT FriendRequests.sender, Users.avatar from (FriendRequests JOIN Users ON FriendRequests.sender = Users.username) WHERE receiver = %s', [request.args.get('username')])

        for req in db_resp:
            arr.append({'username': req[0], 'avatar': req[1]})

        return arr

    def post(self):
        args = request.get_json(force=True)

        exec_commit('INSERT INTO FriendRequests(sender, receiver) VALUES (%s, %s)', [args['sender'], args['receiver']])

        return jsonify(success=True)

class Playing(Resource):
    #send to the backend when a user is playing a new song
    def post(self):
        args = request.get_json(force=True)

        exec_commit('UPDATE Users set currentSongName=%s, currentSongGenre=%s, currentSongArtist=%s, currentSongId=%s, '
                    'currentLat=%s, currentLong=%s WHERE username = %s RETURNING currentSongName',
                               [args['currentSongName'], args['currentSongGenre'], args['currentSongArtist'],
                                args['currentSongId'], args['latitude'], args['longitude'], args['username']])

        #city stuff is tested and should work
        searchArr = ['locality', 'political']
        city = "Rural"
        apireq = "https://maps.googleapis.com/maps/api/geocode/json?latlng=" + str(args['latitude']) + ", " + \
                 str(args['longitude']) + "&key=" + "" + "&result_type=political|locality"
        resp = requests.get(apireq) #make the call to google
        if(resp.status_code==200): #check incase of issues with google api request
            resp = resp.json()['results'][0]['address_components'] #stupid stuff to get down to the right array
            for item in resp:#fine the city
                if(item['types'] == searchArr):#if they're in a city
                    city = item['long_name']


        #add city to locations if it doesnt exist yet
        exec_commit("INSERT INTO Locations(city) VALUES (%s) ON CONFLICT DO NOTHING", [city])

        #add curent song into location history for location average tracking
        exec_commit("INSERT INTO LocationHistory(username, city, playTimeStamp, songName, songGenre, songId, songArtist)"
                    "VALUES (%s, %s, now(), %s, %s, %s, %s)", [args['username'], city, args['currentSongName'],
                                            args['currentSongGenre'], args['currentSongId'], args['currentSongArtist']])

        #remove all songs from location history that are over 24hrs old
        exec_commit("DELETE FROM LocationHistory WHERE playTimeStamp < now() - interval '7 days'")

        #now that all old entries are gone, we can average out the top song/genre and update Locations table
        all_data = exec_get_all("select * from LocationHistory")
        all_songs = {}
        for locInstance in all_data:
            songID = locInstance[5] #5 is the songId
            if songID not in all_songs:
                all_songs[songID] = 0
            else:
                all_songs[songID] += 1

        top_songID = max(all_songs, key=all_songs.get) #grabs the most frequently occuring songID from LocationHistory

        all_genres= {}
        for locInstance in all_data:
            songGenre = locInstance[4] #4 is the songGenre
            if songGenre not in all_genres:
                all_genres[songGenre] = 0
            else:
                all_genres[songGenre] += 1

        topGenre = max(all_genres, key=all_genres.get) #grabs the most frequently occuring songGenre from LocationHistory

        title, artist, songGenre, songId = exec_get_one("SELECT songName, songArtist, songGenre, songId FROM LocationHistory WHERE songId = %s", [top_songID])
        #you could have used the spotify api to get this but i'm special

        #now that we have the top song we can update the location
        exec_commit("UPDATE LOCATIONS SET topSongName=%s, topSongGenre=%s, topSongId=%s, topSongArtist=%s, topGenre=%s",
                    [title, songGenre, songId, artist, topGenre])

        return jsonify(success=True)

class Songs(Resource):

    #gets all people playing songs everywhere to populate the anon map
    def get(self):
        arr = []

        db_resp = exec_get_all('SELECT * from Users where (currentSongName, currentSongGenre, currentSongArtist, '
                               'currentSongId, currentLat, currentLong) IS NOT NULL')


        for pack in db_resp:
            arr.append({
                'location':{
                    'latitude': str(pack[6]),
                    'longitude': str(pack[7]),
                },
                'song':{
                    'name': pack[2],
                    'artist': pack[4],
                    'genre': pack[3],
                    'id': pack[5]
                }
            })

        return arr


class Location(Resource):

    def get(self):
        db_resp = exec_get_all('SELECT topSongName,topSongGenre,topSongId,topSongArtist,topGenre,city from Locations WHERE '
                               'city = %s', [request.args.get('city')])

        if(db_resp == []):
            return {"token": "not found"}, 404

        db_resp = db_resp[0]

        return {
            "city": db_resp[5],
            "song":{
                "name": db_resp[0],
                "artist": db_resp[3],
                "genre": db_resp[1],
                "id": db_resp[2]
            },
            "genre": db_resp[4]
        }

class LocationsFollow(Resource):
    #if location not foudn return a 404 pls
    def post(self):
        args = request.get_json(force=True)
        exec_commit("INSERT INTO LocationFollow(username, city) VALUES (%s, %s)", [args['username'], args['city']])
        return jsonify(success=True)

class LocationsUnfollow(Resource):
    def post(self):
        args = request.get_json(force=True)
        exec_commit("DELETE FROM LocationFollow WHERE username=%s AND city=%s", [args['username'], args['city']])
        return jsonify(success=True)

class LocationsFollowed(Resource):
    def get(self):
        resp = exec_get_all("SELECT city FROM LocationFollow WHERE username=%s", [request.args.get('username')])
        return resp[0]