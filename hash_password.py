# hash_password.py
from werkzeug.security import generate_password_hash

password = "admin123"
hash_pw = generate_password_hash(password)

print(hash_pw)