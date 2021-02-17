import ujson
from bs4 import BeautifulSoup
import urllib3
import time
from tqdm import tqdm
import pickle

def getChemicalCollectionIDs(url = "https://actorws.epa.gov/actorws/actor/2015q3/dataCollections"):

    http = urllib3.PoolManager()
    response = http.request('GET', url)
    soup = BeautifulSoup(response.data,features="html.parser")
    tds = []
    divs = soup.find_all("table")
    for div in divs:
            rows = div.find_all('tr')
            for row in rows :
                tds.append(row.findAll('td'))
    chemical_collection_ids = set()

    for td in tds:
        fields = [t.getText() for t in td]
        try:
            if fields[1] and \
            "UNKNOWN" not in str(fields) and\
            "NA" not in str(fields) and\
            fields[6]=="true" and\
            int(fields[11]) > 0:
                chemical_collection_ids.add(int(fields[0]))
        except:
            pass

    return chemical_collection_ids
   

def getChemicalsFromChemicalCollection(
        chemical_collection_id,
        base_url="https://actorws.epa.gov/actorws/actor/2015q3/dataCollection/chemicals?dataCollectionId"):

    url=base_url+"="+str(chemical_collection_id)
    http = urllib3.PoolManager()
    response = http.request('GET', url)

    soup = BeautifulSoup(response.data,features="html.parser")
    tds = []
    divs = soup.find_all("table")
    for div in divs:
            rows = div.find_all('tr')
            for row in rows :
                tds.append(row.findAll('td'))
    chemical_ids = []
    for td in tds:
        fields = [t.getText() for t in td]
        try:
            chemical_ids.append(fields[1])
            #print(fields[1])
        except:
            pass
    return chemical_ids

def getChemicalHazardSmiles(
        chemical_id,
        base_url="https://actorws.epa.gov/actorws/actor/2015q3/alternateChemicals.html?genericChemicalId"):

    
    url=base_url+"="+str(chemical_id)
    print(url)
    http = urllib3.PoolManager()
    response = http.request('GET', url)

    soup = BeautifulSoup(response.data,features="html.parser")
    tds = []
    divs = soup.find_all("table")
    for div in divs:
            rows = div.find_all('tr')
            for row in rows :
                tds.append(row.findAll('td'))
    safe_fn = open("../datasets/safe.smi","a")
    smiles = []
    sf = False
    for td in tds:
        fields = [t.getText() for t in td]
        try:
            chemid = fields[0]
            smile = fields[4]
            hazard,cancer,chronictox,genetox,devtox,reprotox,foodsafe,biomonitoring = fields[6:14]
            if hazard == "true":
                smiles.append((smile,chemid))
                break
            elif "true" not in fields[7:12] and not sf:
                safe_fn.write(smile+" "+chemid+"\n")
                sf = True
        except:
            pass
    safe_fn.close()
    return smiles



if __name__ == "__main__":   
    try:
        print("loading chemical ids...")
        with open("../datasets/chemical_ids.txt","r")as fn:
            chemical_data = fn.read()
        chemical_ids = [c for c in chemical_data.split("\n")]
        assert(chemical_ids)
        print("done")

    except:
        try:
            print("loading chemical_collection ids...")
            with open("../datasets/chemical_collection_ids.txt","r")as fn:
                chemical_collection_ids = fn.read()
            assert(chemical_collection_ids)
            print("done")
        except:
            chemical_collection_ids = getChemicalCollectionIDs()
            print(len(chemical_collection_ids)," chemical_collections retrieved from actor")
            with open("../datasets/chemical_collection_ids.txt","w")as fn:
                for chem in chemical_collection_ids:
                    fn.write(str(chem)+"\n")
     
        print("retrieving chemical ids from chemical_collections...")
        
        chemical_ids = set()
        for _id in tqdm(chemical_collection_ids):
            cids = getChemicalsFromChemicalCollection(_id)
            for cid in cids:
                chemical_ids.add(cid)
            if len(chemical_ids)>10**4:
                break

        print(len(chemical_ids)," chemical ids collected")
        with open("../datasets/chemical_ids.txt","w")as fn:
            for chem in chemical_ids:
                fn.write(str(chem)+"\n")
    hazard_smiles = set()

    for chem in tqdm(chemical_ids):
        sms = getChemicalHazardSmiles(chem)
        for sm in sms:
            hazard_smiles.add(sm)
        if len(hazard_smiles)>10**3:
                break


    print(len(hazard_smiles)," hazardous chemical representations retrieved")
    with open("../datasets/hazard_smiles.txt","w") as fn:
        for hsm in hazard_smiles:
            fn.write(hsm[0]+" "+str(hsm[1])+"\n")


    
