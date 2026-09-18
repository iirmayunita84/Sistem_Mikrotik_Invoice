from services.mikrotik_service import MikrotikClient


router = {
    "host":"192.168.2.1",
    "username":"irma",
    "password":"yunita",
    "port":8728
}


client = MikrotikClient(
    host=router["host"],
    username=router["username"],
    password=router["password"],
    port=router["port"]
)


print("CONNECTING...")

hasil = client.connect()

print("HASIL CONNECT =", hasil)

if hasil:
    print("API =", client.api)