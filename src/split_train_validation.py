
with open("../datasets/hazard_smiles.txt","r") as fn:
    data = fn.read()

rows = data.split("\n")
print(len(rows),"rows")

train = rows[:800]
test = rows[800:900]
validation = rows[900:]
print("split into",len(train),"training set")
print("split into",len(test),"testing set")
print("split into",len(validation),"validation set")

with open("../datasets/train.smi","w") as fn:
    for row in train:
        fn.write(row+"\n")


with open("../datasets/test.smi","w") as fn:
    for row in test:
        fn.write(row+"\n")


with open("../datasets/valid.smi","w") as fn:
    for row in validation:
        fn.write(row+"\n")



