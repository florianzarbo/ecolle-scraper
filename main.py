import notif
import fetch
import parse

try:
    fetch.fetch_and_save()
except:
    pass

next = parse.get_next_colles()
for colle in next[::-1]:
    notif.send_colle(colle)