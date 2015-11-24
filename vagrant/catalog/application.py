# Import necessary libraries and functions.
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Boardgame, BGItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.client import AccessTokenCredentials
import httplib2
import json
from flask import make_response
import requests

# Initialize flask app
app = Flask(__name__)

# Load JSON for Google Authentication
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Boardgame Piece Tracker"


# Connect to Database and create database session
engine = create_engine('sqlite:///bgdb.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# Code to authenticate via facebook
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output

# Disconnect from from facebook authentication
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

# Authenticate using google
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        # store only the access_token
        login_session['credentials'] = credentials
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    print login_session['user_id']
    print login_session['username']
    print login_session['picture']
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions
# Create a new user
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

# Get the user object
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

# Returns the user_id given an email
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session from google
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Boardgame Information
@app.route('/boardgame/<int:boardgame_id>/JSON')
def boardgameItemJSON(boardgame_id):
    boardgame = session.query(Boardgame).filter_by(id=boardgame_id).one()
    items = session.query(BGItem).filter_by(
        boardgame_id=boardgame_id).all()
    return jsonify(BoardgameItems=[i.serialize for i in items])


@app.route('/boardgame/<int:boardgame_id>/pieces/<int:piece_id>/JSON')
def pieceItemJSON(boardgame_id, piece_id):
    BG_Item = session.query(BGItem).filter_by(id=piece_id).one()
    return jsonify(BoardgameItem=BG_Item.serialize)


@app.route('/catalog.json')
def boardgamesJSON():
    boardgames = session.query(Boardgame).all()
    return jsonify(boardgames=[b.serialize for b in boardgames])

# Show all boardgames
@app.route('/')
@app.route('/boardgame/')
def showBoardgames():
    boardgames = session.query(Boardgame).order_by(asc(Boardgame.name))
    if 'username' not in login_session:
        return render_template('publicboardgames.html', boardgames=boardgames)
    else:
        return render_template('boardgames.html', boardgames=boardgames)

# Create a new boardgame
@app.route('/boardgame/new/', methods=['GET', 'POST'])
def newBoardgame():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newBoardgame = Boardgame(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newBoardgame)
        flash('New Boardgame %s Successfully Created' % newBoardgame.name)
        session.commit()
        return redirect(url_for('showBoardgames'))
    else:
        return render_template('newBoardgame.html')

# Edit a boardgame
@app.route('/boardgame/<int:boardgame_id>/edit/', methods=['GET', 'POST'])
def editBoardgame(boardgame_id):
    editedBoardgame = session.query(
        Boardgame).filter_by(id=boardgame_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedBoardgame.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this boardgame. Please create your own boardgame in order to edit.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedBoardgame.name = request.form['name']
            flash('Boardgame Successfully Edited %s' % editedBoardgame.name)
            return redirect(url_for('showBoardgames'))
    else:
        return render_template('editBoardgame.html', boardgame=editedBoardgame)

# Delete a boardgame
@app.route('/boardgame/<int:boardgame_id>/delete/', methods=['GET', 'POST'])
def deleteBoardgame(boardgame_id):
    boardgameToDelete = session.query(
        Boardgame).filter_by(id=boardgame_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if boardgameToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this boardgame. Please create your own boardgame in order to delete.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(boardgameToDelete)
        flash('%s Successfully Deleted' % boardgameToDelete.name)
        session.commit()
        return redirect(url_for('showBoardgames'))
    else:
        return render_template('deleteBoardgame.html', boardgame=boardgameToDelete)

# Show pieces
@app.route('/boardgame/<int:boardgame_id>/')
@app.route('/boardgame/<int:boardgame_id>/pieces/')
def showPieces(boardgame_id):
    boardgame = session.query(Boardgame).filter_by(id=boardgame_id).one()
    boardgames = session.query(Boardgame).order_by(asc(Boardgame.name))
    creator = getUserInfo(boardgame.user_id)
    items = session.query(BGItem).filter_by(
        boardgame_id=boardgame_id).all()
    if 'username' not in login_session:
        return render_template('publicpieces.html', items=items, boardgame=boardgame, boardgames=boardgames, creator=creator)
    else:
        return render_template('pieces.html', items=items, boardgame=boardgame, boardgames=boardgames, creator=creator, user_id=login_session['user_id'])

# Create a new boardgame piece
@app.route('/boardgame/<int:boardgame_id>/pieces/new/', methods=['GET', 'POST'])
def newBGItem(boardgame_id):
    if 'username' not in login_session:
        return redirect('/login')
    boardgame = session.query(Boardgame).filter_by(id=boardgame_id).one()
    if request.method == 'POST':
        newItem = BGItem(name=request.form['name'], description=request.form['description'], quantity=request.form[
                           'quantity'], boardgame_id=boardgame_id, user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('New boardgame piece %s Successfully Created' % (newItem.name))
        return redirect(url_for('showPieces', boardgame_id=boardgame_id))
    else:
        return render_template('newBGItem.html', boardgame_id=boardgame_id)

# Edit a boardgame piece
@app.route('/boardgame/<int:boardgame_id>/pieces/<int:piece_id>/edit', methods=['GET', 'POST'])
def editBGItem(boardgame_id, piece_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(BGItem).filter_by(id=piece_id).one()
    boardgame = session.query(Boardgame).filter_by(id=boardgame_id).one()
    if request.method == 'POST':
        if login_session['user_id'] != editedItem.user_id:
            return "<script>function myFunction() {alert('You are not authorized to edit this piece to this boardgame. Please create your own boardgame piece in order to edit pieces.');}</script><body onload='myFunction()''>"
        else:
            if request.form['name']:
                editedItem.name = request.form['name']
            if request.form['description']:
                editedItem.description = request.form['description']
            if request.form['quantity']:
                editedItem.quantity = request.form['quantity']
            session.add(editedItem)
            session.commit()
            flash('BG Item Successfully Edited')
            return redirect(url_for('showPieces', boardgame_id=boardgame_id))
    else:
        if login_session['user_id'] != editedItem.user_id:
            return render_template('publicBGItem.html', boardgame_id=boardgame_id, piece_id=piece_id, item=editedItem)
        else:
            return render_template('editBGItem.html', boardgame_id=boardgame_id, piece_id=piece_id, item=editedItem)

# Delete a boardgame piece
@app.route('/boardgame/<int:boardgame_id>/pieces/<int:piece_id>/delete', methods=['GET', 'POST'])
def deleteBGItem(boardgame_id, piece_id):
    if 'username' not in login_session:
        return redirect('/login')
    boardgame = session.query(Boardgame).filter_by(id=boardgame_id).one()
    itemToDelete = session.query(BGItem).filter_by(id=piece_id).one()
    if login_session['user_id'] != itemToDelete.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete piece items to this boardgame. Please create your own boardgame in order to delete items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('BG Item Successfully Deleted')
        return redirect(url_for('showPieces', boardgame_id=boardgame_id))
    else:
        return render_template('deleteBGItem.html', item=itemToDelete)

# Disconnect based on any provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showBoardgames'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showBoardgames'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
