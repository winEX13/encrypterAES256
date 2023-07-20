from betterconf import field, Config
from default import default

de = default()


de.site = 'https://www.centrmag.ru/cryptographer/getActualKey'
de.agent = 'CentrMag Crypto Client/1.0'
de.key = 'kPR2iH2i1Yyn5mNJA4Bl9OiFNOJFcOfP'
de.iv = 'q1G848pZcneqquwT'
de.salt = '@Vzjxno37p1NH6HoLf6T*tiwxkK5C9'
de.tailPassword = '@Vzjxno37p1NH6HoLf6T*tiwxkK5C9'
de.tailHashMode = 'sha512'
de.tailHashSize = 8

#--------------------------------------------------------------

de.dbServer = ''
de.dbLogin = ''
de.dbPassword = ''
de.dbBase = ''
de.dbTableFile = 'cryptographer'
de.dbTableTail = 'cryptographerTail'

class config(Config):
    pass

for key, value in de.items():
    setattr(config, key, field(key, default=value))
