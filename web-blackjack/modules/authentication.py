from modules.base import AppHandler
import re
import random
import hashlib
import hmac
from string import letters
from modules.extras import mixer
from main import Users

'''
Classes and helper functions for SignUp form
'''
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

def valid_username(username):
    return username and USER_RE.match(username)

def valid_password(password):
    return password and PASS_RE.match(password)

def valid_email(email):
    return not email or EMAIL_RE.match(email)

def existing_user(username):
    user = Users.gql("WHERE username = :name", name = username)
    if user.get() == None: return False
    else: return True
    
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_phash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def validate_password(name, password, h):
    salt = h.split(',')[0]
    return h == make_phash(name, password, salt)

def validate(cookie):
    user_id = None
    if cookie:
        cookie_val = check_secure_val(cookie)
        if cookie_val:
            user_id = str(cookie_val)
    return user_id

def hash_str(s):
    return hmac.new(mixer(), s).hexdigest()
    
def make_secure_val(s):
    return "%s|%s" % (s, hash_str(s))
    
def check_secure_val(h):
    s = h.split("|")[0]
    return s if make_secure_val(s) == h else None

class SignUp(AppHandler):
    def get(self):
        user_id = validate(self.request.cookies.get('user_id'))
        if not user_id:
            self.render("signup.html")
        else:
            self.redirect("/")
    
    def post(self):
        error = False
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')
        
        params = dict(username = username, email = email)
        
        if not valid_username(username):
            params['e_user'] = "That's not a valid username."
            error = True
        if not valid_password(password):
            params['e_pass'] = "That's not a valid password."
            error = True
        elif password != verify:
            params['e_ver'] = "Your passwords didn't match."
            error = True
        if not valid_email(email):
            params['e_email'] = "That's not a valid email."
            error = True
            
        prior_user = existing_user(username)
        if prior_user:
            params['e_user'] = "That user already exists."
            error = True
        
        if error:
            self.render("signup.html", **params)
        else:
            u = Users(username = username, 
                      phash = make_phash(username, password), 
                      email = email,
                      chips = 500.0,
                      chipresets = 0,
                      bjwins = 0,
                      bjlosses = 0,
                      bjearnings = 0.0,
                      bjgames = 0)
            user = u.put()
            user_id = make_secure_val(str(user.id()))
            self.response.headers.add_header('Set-Cookie', 'user_id=%s; Path=/' % str(user_id))
            self.redirect("/")

class Login(AppHandler):
    def get(self):
        user_id = validate(self.request.cookies.get('user_id'))
        if not user_id:
            self.render("login.html")
        else:
            self.redirect("/")
    
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        
        user = Users.all().filter('username =', username).get()
        if user:
            phash = user.phash
        
        if user and validate_password(username, password, phash):
            self.response.headers.add_header('Set-Cookie', 'user_id=%s; Path=/' 
                                             % make_secure_val(str(user.key().id())))
            self.redirect('/')
        else:
            self.render('login.html', error = "Invalid Login")
            
class Logout(AppHandler):
    def get(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=%s; Path=/' % "")
        self.response.headers.add_header('Set-Cookie', 'game_id=%s; Path=/' % "")
        self.redirect('/')
            
'''
End classes and helper functions for signup form
'''