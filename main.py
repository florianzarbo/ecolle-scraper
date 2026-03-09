import notif
import fetch
import parse

try:
    open("output/agenda.csv")
except:
    try:
        fetch.fetch_and_save()
    except:
        pass
    pass

next = parse.get_next_colles()
for colle in next[::-1]:
    notif.send_colle(colle)