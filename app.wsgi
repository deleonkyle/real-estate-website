#flaskapp.wsgi
import sys
sys.path.insert(0, '/var/www/html/real-estate-website')
 
from app import app as application