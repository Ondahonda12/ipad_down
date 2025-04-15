import requests
import json
import os
import hashlib
import pymysql.cursors
import time
from tqdm import tqdm

# Nastavení připojení k DB a výstupní cesta
host = 'localhost'
user = 'root'
password = 'tvojeheslo'
db = 'tvojedb'
path = './ipsw'

USE_PYCRYPTODOME = False
try:
    from Crypto.Hash import MD5
    USE_PYCRYPTODOME = True
except:
    import hashlib

def ecid_r(name):
    try:
        connection = pymysql.connect(
            host=host, user=user, password=password, db=db,
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `ios_status` WHERE `name`=%s ORDER BY id DESC LIMIT 1"
            cursor.execute(sql, (name,))
            result = cursor.fetchone()
        connection.close()
        return result
    except Exception as e:
        print(e)

def download(url, expected_md5, output_dir):
    if not url.endswith('.ipsw'):
        print("URL není IPSW soubor.")
        return

    fn = os.path.basename(url)
    filepath = os.path.join(output_dir, fn)

    if os.path.exists(filepath):
        print(f"Kontroluji {fn} ...")
        md5 = MD5.new() if USE_PYCRYPTODOME else hashlib.md5()
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                md5.update(chunk)
        if md5.hexdigest().lower() == expected_md5.lower():
            print(f"{fn} už existuje a hash sedí, přeskočeno.\n")
            return
        else:
            print(f"Špatný hash, mažu {fn}")
            os.remove(filepath)

    print(f"Stahuji {fn} ...")
    md5 = MD5.new() if USE_PYCRYPTODOME else hashlib.md5()
    for attempt in range(10):
        try:
            r = requests.get(url, stream=True)
            total = int(r.headers.get('Content-Length', 0))
            with open(filepath, 'wb') as f:
                with tqdm(total=total, unit='B', unit_scale=True) as pbar:
                    for chunk in r.iter_content(1024):
                        if chunk:
                            f.write(chunk)
                            md5.update(chunk)
                            pbar.update(len(chunk))
            if md5.hexdigest().lower() != expected_md5.lower():
                print("Hash MISMATCH!")
            else:
                print("Hash OK")
            return
        except requests.exceptions.RequestException:
            print(f"Pokus {attempt + 1} selhal, čekám...")
            time.sleep(5)
    print(f"Stahování {fn} selhalo po 10 pokusech.")

def ipsw_link(ios_ver):
    url_l = []
    data = requests.get(f"https://api.ipsw.me/v4/ipsw/{ios_ver}").json()
    iPads = ["iPad15,6", "iPad15,7", "iPad14,1"]
    for item in data:
        if item["identifier"] in iPads:
            url_l.append(f'{item["url"]};{item["md5sum"]}')
    return list(set(url_l))  # odstraní duplikáty

def main():
    os.makedirs(path, exist_ok=True)
    all_links = ipsw_link("18.4")
    all_pass = []

    for entry in all_links:
        url, md5h = entry.split(";")
        try:
            print(f"\nURL: {url}")
            download(url, md5h, path)
            all_pass.append("PASS")
        except Exception as e:
            print(f"Chyba při stahování: {e}")
            all_pass.append("FAIL")

    if "FAIL" in all_pass:
        print("Něco se pokazilo.")
    else:
        print("Všechno v pohodě, můžeš poslat email a aktualizovat DB.")

if __name__ == "__main__":
    main()
