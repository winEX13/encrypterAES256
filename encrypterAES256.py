import os
from base64 import b64encode, b64decode
import hashlib
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import cryptocode
import requests
import json
from webDatabase import webDb as db
from tqdm import tqdm
from collections import Counter as count
from transliterate import translit
import shutil
# import pyminizip
from settings import config

class encrypter(object):
    def __init__(self, func=None, *args) -> None:
        self.func = func
        self.args = args
        self.config = config()
        # self.dbConfig = dbConfig()
        # self.tailHashSize = 8

    def action(self):
        try:
            return(getattr(self, self.func)(*self.args))
        except AttributeError:
            return(False)

    # def pad16(self, data):
    #     if isinstance(data, bytes):
    #         data = data+bytes([16-len(data)%16])*(16-len(data)%16) if len(data)%16 != 0 else data
    #     elif isinstance(data, str):
    #         data = data+chr(16-len(data)%16)*(16-len(data)%16) if len(data)%16 != 0 else data
    #     else:
    #         return(False)
    #     return(data)

    # def padX(self, data, l):
    #     self.padVal = l
    #     if isinstance(data, bytes):
    #         data = data+bytes([l-len(data)%l])*(l-len(data)%l)
    #     elif isinstance(data, str):
    #         data = data+chr(l-len(data)%l)*(l-len(data)%l)
    #     else:
    #         return(False)
    #     return(data)

    # def unpad(self, data):
    #     unpad = lambda s : s[:-s[-1]]
    #     data = unpad(data) if len(data)%32 != 0 else data
    #     return(data)

    def bigDataRead(self, obj, buffer: int):
        while True:
            data = obj.read(buffer)
            if not data:
                break
            yield(data)

    def getCipher(self, key: str, iv: str):
        return(AES.new(key.encode(), AES.MODE_CBC, iv=iv.encode()))

    def getKeysFromDb(self, hash: str):
        connect = db(self.config.dbServer, self.config.dbLogin, self.config.dbPassword, self.config.dbBase)
        try:
            key, iv = connect.find(self.config.dbTableFile, '`key`, iv', f'hash = "{hash}"')[0]
        except Exception as e:
            return(False, e)
        connect.disconnect()
        if hashlib.md5((key + iv).encode()).hexdigest() == hash:
            return(key, iv)
        else:
            return(False)

    def getTailPassword(self):
        connect = db(self.config.dbServer, self.config.dbLogin, self.config.dbPassword, self.config.dbBase)
        hashTail = self.hashShake(self.config.tailPassword, length=self.config.tailHashSize)
        if len(connect.find(self.config.dbTableTail, '*', f'`key` = "{self.config.tailPassword}"')) == 0:
            connect.add(self.config.dbTableFile, [self.config.tailPassword, hashTail])
        connect.disconnect()
        return(hashTail.encode('ascii'))

    def getActualKey(self):
        return(json.loads(self.decrypt(json.loads(requests.get(self.config.site, headers={'User-Agent': self.config.agent}).text)['data'], self.getCipher(self.config.key, self.config.iv))))

    def getActualCipher(self):
        cryptData = self.getActualKey()
        return({'cipher': self.getCipher(cryptData['key'], cryptData['iv']), 'hash': cryptData['hash']})

    def fileData(self, inFile, sliceSize: int):
        slices = self.bigDataRead(open(inFile, 'rb'), sliceSize)
        size = os.path.getsize(inFile)
        outFile, ext = os.path.splitext(inFile)
        # outFile = outFile + '.cry'
        return({'slices': slices, 'size': size, 'ext': ext, 'outFile': outFile})

    def hashShake(self, seed: str, length: int=8, size: int=256) -> str:
        if size in (128, 256):
            hashObj = getattr(hashlib, f'shake_{size}')
        else:
            raise Exception('size can be 128 or 256')
        if length < 0:
            raise Exception('length must be greater than 0')
        else:
            return(hashObj(seed.encode()).hexdigest(length))

    def checksumCreate(self, dataList: list, hashMode: str='sha512'):
        try:
            hashObj = getattr(hashlib, hashMode)
        except Exception as e:
            raise Exception(e)
        data = ''
        for el in dataList:
            data += str(el)
        return(hashObj((f'{data}{self.config.salt}').encode()).hexdigest())
    
    def tailCreate(self, size: int, dataSize: int, lastSliceSize: int, ext: str, hashFile: str, checksumObj: str):
        return(
            json.dumps(
                {
                    'sliceSize': dataSize, 
                    'lastSliceSize': lastSliceSize, 
                    'ext': ext, 
                    'hash': hashFile, 
                    'checksum': self.checksumCreate([size, checksumObj, ext, hashFile], hashMode=self.config.tailHashMode)
                }
            )
        )

    def checker(self, func, *args):
        execution, message = getattr(self, func)(*args)
        if not execution:
            return(False)
        else:
            return(True)

    def encrypt(self, data: bytes, cipher):
        return(b64encode(cipher.encrypt(pad(data, 16))))

    def encryptFile(self, inFile, strict=True, sliceSize=2**17):
        try:
            actualCipher = self.getActualCipher()
            hashFile = actualCipher['hash']
            fileData = self.fileData(inFile, sliceSize)
            size = fileData['size']
            ext = fileData['ext']
            outFile = fileData['outFile']
            if ext == '.cry':
                return(False, 'file is encrypted')
            if not strict:
                [os.remove(path) for path in (outFile, f'{outFile}.cry', f'{outFile}{ext}.cry') if os.path.exists(path)]
            if not (os.path.exists(outFile) and os.path.exists(f'{outFile}.cry') and os.path.exists(f'{outFile}{ext}.cry')):
                with open(outFile, 'ab+') as of:
                    with tqdm(range(size), f'encrypting [{os.path.split(inFile)[-1]}]', unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                        slicesSize = []
                        checksumObj = hashlib.sha512()
                        for slice in fileData['slices']:
                            data = self.encrypt(slice, actualCipher['cipher'])
                            slicesSize.append(len(data))
                            checksumObj.update(data)
                            of.write(data)
                            pbar.update(len(slice))
                    try:
                        dataSize, lastSliceSize = [obj for obj, count_ in count(slicesSize).most_common()]
                    except ValueError as e:
                        dataSize = lastSliceSize = len(data)
                    config = self.tailCreate(size, dataSize, lastSliceSize, ext, hashFile, checksumObj.hexdigest())
                    config = cryptocode.encrypt(config, self.config.tailPassword).encode('ascii')
                    of.write(config)
                    of.write(self.getTailPassword())
                    of.write((len(config)).to_bytes(10, byteorder='little'))
            else:
                return(False, 'file exists')
        except Exception as e:
            return(False, e)
        else:
            outFileOriginal = outFile
            if not os.path.exists(f'{outFile}.cry'):
                outFile = f'{outFile}.cry'
            else:
                outFile = f'{outFile}{ext}.cry'
            os.rename(outFileOriginal, outFile)
            return(True, json.dumps({'path': os.path.abspath(outFile).replace('\\', '/')}))

    def encryptFiles(self, inFiles, strict=True, sliceSize=2**17):
        errors = []
        try:
            actualCipher = self.getActualCipher()
            hashFile = actualCipher['hash']
        except Exception as e:
            return(False, e)

        for inFile in tqdm(inFiles, unit='unit', unit_scale=True, unit_divisor=1000):
            try:
                fileData = self.fileData(inFile, sliceSize)
                size = fileData['size']
                ext = fileData['ext']
                outFile = fileData['outFile']
                if ext == '.cry':
                    errors.append((inFile, 'file is encrypted'))
                    break
                if not strict:
                    [os.remove(path) for path in (outFile, f'{outFile}.cry', f'{outFile}{ext}.cry') if os.path.exists(path)]
                if not (os.path.exists(outFile) and os.path.exists(f'{outFile}.cry') and os.path.exists(f'{outFile}{ext}.cry')):
                    with open(outFile, 'ab+') as of:
                        slicesSize = []
                        checksumObj = hashlib.sha512()
                        for slice in fileData['slices']:
                            data = self.encrypt(slice, actualCipher['cipher'])
                            slicesSize.append(len(data))
                            checksumObj.update(data)
                            of.write(data)
                        try:
                            dataSize, lastSliceSize = [obj for obj, count_ in count(slicesSize).most_common()]
                        except ValueError as e:
                            dataSize = lastSliceSize = len(data)
                        config = self.tailCreate(size, dataSize, lastSliceSize, ext, hashFile, checksumObj.hexdigest())
                        config = cryptocode.encrypt(config, self.config.tailPassword).encode('ascii')
                        of.write(config)
                        of.write(self.getTailPassword())
                        of.write((len(config)).to_bytes(10, byteorder='little'))
                    if not self.decryptFile(f'{os.path.splitext(inFile)[0]}.cry', outPathMode=3)[0]:
                        errors.append((inFile, 'file failed decrypt test'))
                else:
                    errors.append((inFile, 'file exists'))
                outFileOriginal = outFile
                if not os.path.exists(f'{outFile}.cry'):
                    outFile = f'{outFile}.cry'
                else:
                    outFile = f'{outFile}{ext}.cry'
                os.rename(outFileOriginal, outFile)
            except Exception as e:
                errors.append((inFile, e))
        if os.path.exists(f'{os.environ["TEMP"]}/test'):
            shutil.rmtree(f'{os.environ["TEMP"]}/test')
        return(True, errors)

    def decrypt(self, data, cipher):
        return(unpad(cipher.decrypt(b64decode(data)), 16))

    # def toZip(self, outFile: str, ext: str):
    #     translitOutFile = translit(f'{outFile}{ext}', language_code='ru', reversed=True)
    #     translitOutFile = f'{outFile}{ext}'
    #     os.rename(outFile, translitOutFile)
    #     outFileZip = os.path.splitext(translitOutFile)[0] + '.zip'
    #     pyminizip.compress(translitOutFile, None, outFileZip, self.config.zipPassword, 1)
    #     os.remove(translitOutFile)
    #     return(os.path.abspath(outFileZip).replace('\\', '/'))

    def decryptFile(self, inFile: str, outPathMode: int=0, toZip: bool=False):
        try:
            if not os.path.exists(inFile):
                return(False, 'file not exists')
            if os.path.splitext(inFile)[-1] != '.cry':
                return(False, 'file is not encrypted')
            name = os.path.basename(inFile).replace(".cry", "")
            if outPathMode == 0:
                folder = self.hashShake(inFile)
                if not os.path.exists(f'{os.environ["TEMP"]}/{folder}'):
                    os.mkdir(f'{os.environ["TEMP"]}/{folder}')
                outFile = f'{os.environ["TEMP"]}/{folder}/{name}'
            elif outPathMode == 1:
                folder = os.path.dirname(inFile)
                if not os.path.exists(f'{folder}/decodes'):
                    os.mkdir(f'{folder}/decodes')
                outFile = f'{folder}/decodes/{name}'
            elif outPathMode == 2:
                folder = os.environ["TEMP"]
                if not os.path.exists(f'{folder}/decodes'):
                    os.mkdir(f'{folder}/decodes')
                outFile = f'{folder}/decodes/{name}'
            elif outPathMode == 3:
                folder = f'{os.environ["TEMP"]}/test'
                if not os.path.exists(folder):
                    os.mkdir(folder)
                outFile = f'{folder}/test'
            else:
                return(False, 'wrong outpath mode')     
            with open(outFile, 'ab+') as of:
                outSize = 0
                for slice in self.decryptBytes(inFile):
                    decryptData = slice['decryptData']
                    of.write(decryptData)
                    checksumObj = slice['checksumObj']
                    ext = slice['ext']
                    hashFile = slice['hash']
                    checksum = slice['checksum']
                    outSize += len(decryptData)
                if checksum != self.checksumCreate([outSize, checksumObj.hexdigest(), ext, hashFile], hashMode=self.config.tailHashMode):
                    os.remove(outFile)
                    return(False, 'wrong data')
        except Exception as e:
            return(False, e)
        else:
            try:
                os.remove(outFile + ext)
            except FileNotFoundError:
                pass
            if toZip:
                pass
                # return(True, json.dumps({'path': self.toZip(outFile, ext), 'password': self.config.zipPassword}))
            else:
                os.rename(outFile, f'{outFile}{ext}')
                return(True, json.dumps({'path': f'{outFile}{ext}'}))

    def decryptBytes(self, inFile):
        try:
            if not os.path.exists(inFile):
                return(False, 'file not exists')
            if os.path.splitext(inFile)[-1] != '.cry':
                return(False, 'file is not encrypted')
            if os.path.getsize(inFile) != 0:
                size = os.path.getsize(inFile)
                with open(inFile, 'rb') as ifl:
                    ifl.seek(-10, 2)
                    zeros = int.from_bytes(ifl.read(), byteorder='little') + self.config.tailHashSize * 2
                    ifl.seek(-1 * zeros - 10, 2)
                    fileСonfig = json.loads(cryptocode.decrypt(ifl.read(zeros).decode('ascii'), self.config.tailPassword))
                    sliceSize = fileСonfig['sliceSize']
                    lastSliceSize = fileСonfig['lastSliceSize']
                    ext = fileСonfig['ext']
                    hashFile = fileСonfig['hash']
                    checksum = fileСonfig['checksum']
                keyData = self.getKeysFromDb(hashFile)
                if keyData:
                    cipherСonfig = self.getCipher(*keyData)
                else:
                    return(False, 'wrong hash')
                slices = self.bigDataRead(open(inFile, 'rb'), sliceSize)
                with tqdm(range(size), f'decrypting [{os.path.split(inFile)[-1]}]', unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                    checksumObj = hashlib.sha512()
                    for slice in slices:
                        if len(slice) == sliceSize:
                            decryptData = self.decrypt(slice, cipherСonfig)
                            checksumObj.update(slice)
                            yield({'decryptData': decryptData, 'checksumObj': checksumObj, 'ext': ext, 'hash': hashFile, 'checksum': checksum})
                        elif len(slice) == lastSliceSize + zeros + 10:
                            decryptData = self.decrypt(slice[:lastSliceSize], cipherСonfig)
                            checksumObj.update(slice[:lastSliceSize])
                            yield({'decryptData': decryptData, 'checksumObj': checksumObj, 'ext': ext, 'hash': hashFile, 'checksum': checksum})
                        pbar.update(len(slice))                
        except Exception as e:
            return(False, e)

    # def decryptSlices(self, inFile):
    #     try:
    #         if not os.path.exists(inFile):
    #             return(False, 'file not exists')
    #         if os.path.splitext(inFile)[-1] != '.cry':
    #             return(False, 'file is not encrypted')
    #         if os.path.getsize(inFile) != 0:
    #             size = os.path.getsize(inFile)
    #             with open(inFile, 'rb') as ifl:
    #                 ifl.seek(-10, 2)
    #                 zeros = int.from_bytes(ifl.read(), byteorder='little')
    #                 ifl.seek(-1 * zeros - 10, 2)
    #                 fileСonfig = json.loads(ifl.read(zeros))
    #                 sliceSize = fileСonfig['sliceSize']
    #                 lastSliceSize = fileСonfig['lastSliceSize']
    #                 ext = fileСonfig['ext']
    #                 hashFile = fileСonfig['hash']
    #                 checksum = fileСonfig['checksum']
    #             keyData = self.getKeysFromDb(hashFile)
    #             if keyData:
    #                 cipherСonfig = self.getCipher(*keyData)
    #             else:
    #                 return(False, 'wrong hash')
    #             random.seed(inFile)
    #             folder = urlsafe_b64encode(random.randbytes(12)).decode('ascii')
    #             if not os.path.exists(f'{os.environ["TEMP"]}/{folder}'):
    #                 os.mkdir(f'{os.environ["TEMP"]}/{folder}')
    #             slices = self.bigDataRead(open(inFile, 'rb'), sliceSize)
    #             with tqdm(total=size) as pbar:
    #                 checksumObj = hashlib.sha512()
    #                 outSize = 0
    #                 order = []
    #                 for slice in slices:
    #                     if len(slice) == sliceSize:
    #                         decryptData = self.decrypt(slice, cipherСonfig)
    #                         checksumObj.update(slice)
    #                         outSize += len(decryptData)
    #                     elif len(slice) == lastSliceSize + zeros + 10:
    #                         decryptData = self.decrypt(slice[:lastSliceSize], cipherСonfig)
    #                         checksumObj.update(slice[:lastSliceSize])
    #                         outSize += len(decryptData)
    #                     pbar.update(len(slice))
    #                     random.seed(decryptData)
    #                     name = urlsafe_b64encode(random.randbytes(8)).decode('ascii')
    #                     outFile = f'{os.environ["TEMP"]}/{folder}/{name}'
    #                     with open(outFile, 'wb') as of:
    #                         of.write(decryptData)
    #                     order.append(os.path.abspath(outFile).replace('\\', '/'))
    #                 if checksum != hashlib.sha512((str(outSize) + checksumObj.hexdigest() + ext + hashFile + '@Vzjxno37p1NH6HoLf6T*tiwxkK5C9').encode()).hexdigest():
    #                     shutil.rmtree(f'{os.environ["TEMP"]}/{folder}')
    #                     return(False, 'wrong data')
    #     except Exception as e:
    #         return(False, e)
    #     else:
    #         return(True, (tuple(order), ext))
