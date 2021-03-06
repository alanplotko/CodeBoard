#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
import bottle
import pymongo

bottle.debug(True)

mongo_con = pymongo.Connection(os.environ['OPENSHIFT_MONGODB_DB_HOST'],
                               int(os.environ['OPENSHIFT_MONGODB_DB_PORT']))

mongo_db = mongo_con[os.environ['OPENSHIFT_APP_NAME']]
mongo_db.authenticate(os.environ['OPENSHIFT_MONGODB_DB_USERNAME'],
                      os.environ['OPENSHIFT_MONGODB_DB_PASSWORD'])


# client = pymongo.MongoClient()
 
# mongo_db = client.codeboard
# mongo_db.authenticate(os.environ['OPENSHIFT_MONGODB_DB_USERNAME'],
#                      os.environ['OPENSHIFT_MONGODB_DB_PASSWORD'],
#                      'codeboard')

def user_find(email):
  """Returns a user DB entry by using the user's email address."""
  if not email: return None
  return mongo_db.users.find_one({ '_id': email})

@bottle.route('/', method="POST")
def index():
  """Controls the form on index.html. Either registers the user or tells them they already have an account."""
  data = bottle.request.forms
  if data.get('email'):
    # check for pre existance
    tuser = user_find(data.get('email'))
    if tuser:
      return bottle.template('index', result='You are already registered!')
    else:
      nuser = {
        '_id': data.get('email'),
        'pw': data.get('password')
      }
      userid = mongo_db.users.insert(nuser)
      return bottle.template('welcome', result='You\'ve been signed up!', email=data.get('email'))
  else:
    return bottle.template('index', result=None)

@bottle.route('/')
def index():
  """Loads the basic template for index.html"""
  return bottle.template('index')

def snippet_create(user, code):
  """Creates a code snippet and inserts it into the snippets MongoDB table."""
  nsnippet = {
    '_id': uuid.uuid4().hex,
    'uid': user['_id'],
    'code': code
    }
  mongo_db.snippets.insert(nsnippet)
  return nsnippet

def note_create(snip, user, text):
  """Creates a note and inserts it into the notes MongoDB table."""
  nnote = {
    '_id': uuid.uuid4().hex,
    'uid': user['_id'],
    'cid': snip['_id'],
    'text': text
  }
  mongo_db.notes.insert(nnote)

def annote_create(snip, user, text):
  """Creates an annote and inserts it into the notes MongoDB table."""
  nannote = {
    '_id': uuid.uuid4().hex,
    'uid': user['_id'],
    'cid': snip['_id'],
    'text': text
  }
  mongo_db.notes.insert(nannote)

def user_list():
  """Returns a list of registered users' email addresses."""
  l = []
  for u in mongo_db.users.find():
    l.append(u['_id'])
  l.sort()
  return l

def snippet_list(user):
  """Returns a list of code snippets that belong to user."""
  l = []
  #speed issues?
  for s in mongo_db.snippets.find():
      if s['uid'] == user:
        l.append(s)
  l.sort()
  return l

def note_list(snippet):
  """Returns a list of notes that are tagged on snippet."""
  l = []
  #speed?
  for n in mongo_db.notes.find():
    if n['cid'] == snippet:
      l.append(n)
  l.sort()
  return l

def annote_list(snippet):
  """Returns a list of annotes that are tagged on snippet."""
  l = []
  #speed?
  for a in mongo_db.annotes.find():
    if a['cid'] == snippet:
      l.append(a)
  l.sort()
  return l

def user_auth(user, pw):
  """Checks if user and password match. Temporary."""
  if not user: return False
  return user['pw'] == pw

def snippet_find_by_id(snip_id):
  """Finds a code snippet by its uuid."""
  if not snip_id: return None
  return mongo_db.snippets.find_one({ '_id': snip_id})

#anti-hax
reserved_usernames = 'home signup login logout post static DEBUG note annote'

bottle.TEMPLATE_PATH.append(os.path.join(os.environ['OPENSHIFT_REPO_DIR'], 'views'))

def get_session():
  session = bottle.request.get_cookie('session', secret='secret')
  return session

def save_session(uid):
  session = {}
  session['uid'] = uid
  session['sid'] = uuid.uuid4().hex
  bottle.response.set_cookie('session', session, secret='secret')
  return session

def invalidate_session():
  bottle.response.delete_cookie('session', secret='secret')
  return

@bottle.route('/dashboard')
def dashboard():
  session = get_session()
  if not session: bottle.redirect('/login')
  luser = user_find(session['uid'])
  if not luser: bottle.redirect('/logout')
  
  # bottle.TEMPLATES.clear()
  return bottle.template('dashboard',
                         # postlist=postlist,
                         # userlist=user_list(),
                         page='dashboard',
                         username=luser['_id'],
                         logged=True)

@bottle.route('/snippets', method="POST")
def post_snippet():
  session = get_session()
  luser = user_find(session['uid'])
  if not luser: bottle.redirect('/logout')  
  # bottle.TEMPLATES.clear()
  data = bottle.request.forms
  if data.get('code'):
    snip = snippet_create(luser, data.get('code'))
    bottle.redirect('/snippets/' + str(snip['_id']))

@bottle.route('/snippets/<id>')
def snippet_page(id):
    session = get_session()
    luser = user_find(session['uid'])
    if not luser: bottle.redirect('/logout')
    snippet = snippet_find_by_id(id)
    if not snippet:
        return bottle.HTTPError(code=404, message='snippet not found')
    return bottle.template('snips',
                            author=snippet['uid'],
                            snip_id=id,
                            snippet=snippet,
                            code=snippet['code'],
                            page='snips',
                            annotes=annote_list(snippet),
                            notes=note_list(snippet),
                            logged=(session != None))

@bottle.route('/note/<snip>', method='POST')
def note(snip):
  session = get_session()
  if not session: bottle.redirect('/login')
  luser = user_find(session['uid'])
  if not luser: bottle.redirect('/logout')
  if 'text' in bottle.request.POST:
    text = bottle.request.POST['text']
    note_create(snip, luser, text)

@bottle.route('/annote/<snip>', method='POST')
def annote(snip):
  session = get_session()
  if not session: bottle.redirect('/login')
  luser = user_find(session['uid'])
  if not luser: bottle.redirect('/logout')
  if 'text' in bottle.request.POST:
    text = bottle.request.POST['text']
    annote_create(snip, luser, text)

# @bottle.route('/signup')
@bottle.route('/login')
def get_login():
  session = get_session()
  # bottle.TEMPLATES.clear()
  if session: bottle.redirect('/dashboard')
  return bottle.template('login',
			 page='login',
			 error_login=False,
			 error_signup=False,
			 logged=False)

@bottle.route('/login', method='POST')
def post_login():
  if 'email' in bottle.request.POST and 'password' in bottle.request.POST:
    email = bottle.request.POST['email']
    password = bottle.request.POST['password']
    user = user_find(email)
    if user_auth(user, password):
      save_session(user['_id'])
      bottle.redirect('/dashboard')
  return bottle.template('login',
			 page='login',
			 error_login=True,
			 error_signup=False,
			 logged=False)

@bottle.route('/logout')
def logout():
  invalidate_session()
  bottle.redirect('/')

# @bottle.route('/signup', method='POST')
# def post_signup():
#   if 'name' in bottle.request.POST and 'password' in bottle.request.POST:
#     name = bottle.request.POST['name']
#     password = bottle.request.POST['password']
#     if name not in reserved_usernames.split():
#       userid = user_create(name, password)
#       if userid:
#         save_session(userid)
#         bottle.redirect('/home')
#     return bottle.template('login',
# 			   page='login',
# 			   error_login=False,
# 			   error_signup=True,
# 			   logged=False)

@bottle.route('/DEBUG/cwd')
def dbg_cwd():
  return "<tt>cwd is %s</tt>" % os.getcwd()

@bottle.route('/DEBUG/env')
def dbg_env():
  env_list = ['%s: %s' % (key, value)
              for key, value in sorted(os.environ.items())]
  return "<pre>env is\n%s</pre>" % '\n'.join(env_list)

@bottle.route('/static/assets/<filename:path>', name='static')
def static_file(filename):
  return bottle.static_file(filename, root=os.path.join(os.environ['OPENSHIFT_REPO_DIR'], 'static/assets'))

application = bottle.default_app()
