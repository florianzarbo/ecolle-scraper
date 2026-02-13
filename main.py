import notif
import fetch
import parse

try:
    a = open("output/agenda.csv")
    a.close()
except:
    fetch.fetch_and_save()

next = parse.get_next_colles()
for colle in next[::-1]:
    notif.send_colle(colle)