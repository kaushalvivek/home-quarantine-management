from flask_app import *
import gspread
import pandas as pd
import dateparser

# get currently active patients
print("Reading google sheet ...")
try:
  gc = gspread.service_account()
  sh = gc.open("Patna Home Quarantine")
  all_values = sh.sheet1.get_all_values()
  data = pd.DataFrame(all_values)
  print("Google sheet successfully read!")
except:
  print("ERROR : Could not connect to sheet")
active = data.loc[data.iloc[:,7]=="Active"]

# get current operators
operators = Operators.query.all()

# assign operators
patients = []
for i in range(0, active.shape[0]):
  patient = {
    'pid':active.iloc[i,0],
    'name':active.iloc[i,1],
    'mobile':active.iloc[i,5],
    'age':active.iloc[i,2],
    'sex':active.iloc[i,3],
    'address':active.iloc[i,4],
    'op_id':operators[i%len(operators)].op_id,
    'contacted':"no"
  }
  patients.append(patient)

# remove old entries from database
db.session.query(CurrentPatients).delete()

# push to database
for i in range(0,len(patients)):
  new_patient = CurrentPatients(name=patients[i]['name'],\
  pid=patients[i]['pid'],mobile=patients[i]['mobile'],\
  op_id=patients[i]['op_id'],age=patients[i]['age'],\
  sex=patients[i]['sex'],address=patients[i]['address'],\
  contacted=patients[i]['contacted'])
  db.session.add(new_patient)

db.session.commit()

print(len(patients),"active patients added")