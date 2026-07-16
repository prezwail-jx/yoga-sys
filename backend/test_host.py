import socket
import psycopg2

try:
    print("Testing host.docker.internal...")
    conn = psycopg2.connect("host=host.docker.internal port=5433 user=yoga password=yoga dbname=yoga_sys")
    print("SUCCESS!")
except Exception as e:
    print("ERROR:", e)
