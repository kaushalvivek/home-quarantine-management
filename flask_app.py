import os 
from flask import Flask, render_template, url_for, redirect, request, jsonify, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
import random , string
import pandas as pd
import configparser

path = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
SESSION_TYPE = 'filesystem'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///store.db'
db = SQLAlchemy(app)

app.config.from_object(__name__)
Session(app)

class Operators(db.Model):
  op_id = db.Column(db.String, primary_key=True)
  name = db.Column(db.String)
  email = db.Column(db.String, unique=True)
  password = db.Column(db.String)
  date_created = db.Column(db.DateTime)

class CurrentPatients(db.Model):
  pid = db.Column(db.String, primary_key=True)
  name = db.Column(db.String)
  mobile = db.Column(db.String)
  age = db.Column(db.String)
  sex =  db.Column(db.String)
  address = db.Column(db.String)
  op_id = db.Column(db.String)
  contacted = db.Column(db.String)

class OperatorLog(db.Model):
  tran_id = db.Column(db.String, primary_key=True)
  date = db.Column(db.DateTime)
  op_id = db.Column(db.String)
  assigned = db.Column(db.Integer)
  contacted = db.Column(db.Integer)
  unreachable = db.Column(db.Integer)

class PatientLog(db.Model):
  tran_id = db.Column(db.String, primary_key=True)
  date = db.Column(db.DateTime)
  pid = db.Column(db.String)
  symptoms = db.Column(db.String)

class Symptoms(db.Model):
  symptom_id = db.Column(db.String, primary_key=True)
  name = db.Column(db.String)
  date_created = db.Column(db.DateTime)

# hourly automated in backend:
# - fill current patients
# - assign operator

# home page
@app.route('/')
def index():
  # if operator is logged in
  if "operator" in session:
    # get patients using op_id
    symptoms = Symptoms.query.all()
    op_id = session['operator'].op_id
    patients_table = pd.read_sql("SELECT * from current_patients where op_id=="+op_id+";", db.session.bind)
    if patients_table.shape[0] == 0:
      return render_template('operator_login.html', wrong=False)
    to_contact_patients = []
    contacted_patients = []
    unreachable_patients = []
    for i in range(0,patients_table.shape[0]):
      patient = {
        'pid':patients_table.iloc[i,0],
        'name':patients_table.iloc[i,1],
        'mobile':patients_table.iloc[i,2],
        'age':patients_table.iloc[i,3],
        'sex':patients_table.iloc[i,4],
        'address':patients_table.iloc[i,5],
        'contacted':patients_table.iloc[i,7],
      }
      if patients_table.iloc[i,7] == "no":
        to_contact_patients.append(patient)
      elif patients_table.iloc[i,7] == "contacted":
        contacted_patients.append(patient)
      else:
        unreachable_patients.append(patient)
    to_contact = len(to_contact_patients)
    contacted = len(contacted_patients)
    unreachable = len(unreachable_patients)
    
    return render_template('index.html',
    to_contact_patients=to_contact_patients,
     to_contact=to_contact,
     contacted=contacted,
     unreachable=unreachable,
     name=session['operator'].name,
     unreachable_patients = unreachable_patients,
     symptoms = symptoms
     )
  else:
    return render_template('operator_login.html', wrong=False)

# mark patients as contacted
@app.route('/contact')
def contact():
  if "operator" in session:
    tran_id = random.randint(1000000000,9999999999)
    pid = request.args.get('pid')
    symptoms = request.args.get('symptoms')
    print(symptoms)
    created = datetime.now()
    new_patient_log = PatientLog(tran_id=tran_id, pid=pid,date=created,symptoms=symptoms)
    db.session.add(new_patient_log)
    patient = CurrentPatients.query.filter_by(pid=pid).first()
    patient.contacted = "contacted"
    db.session.commit()
    return redirect('/')
  else:
    return render_template('operator_login.html', wrong=False)

# mark patients as unreachable
@app.route('/unreachable')
def unreachable():
  if "operator" in session:
    pid = request.args.get('pid')
    patient = CurrentPatients.query.filter_by(pid=pid).first()
    patient.contacted = "unreachable"
    db.session.commit()
    return redirect('/')
  else:
    return render_template('operator_login.html', wrong=False)

# log out and exit session
@app.route('/logout')
def logout():
  session.clear()
  return redirect('/')

# verification of admin ID and password
@app.route('/admin_verify')
def admin_verify():
    # to be set by config later
  session['admin_email'] = "vivek.kaushal@outlook.com"
  session['admin_password'] = 'temp'
  password = request.args.get('password')
  email = request.args.get('email')
  if password == session.get('admin_password') \
  and email.lower() == session.get("admin_email"):
    session['signin_key'] = 'sadewiapexfdiblrnnwuludogkqyuazp'
    return redirect('/admin_page')
  else:
    return render_template('admin_login.html',wrong=True)


# verification of operator ID and password
@app.route('/operator_verify')
def operator_verify():
  password = request.args.get('password')
  email = request.args.get('email').lower()
  operator = Operators.query.filter(Operators.email.in_([email]), Operators.password.in_([password]))
  result = operator.first()
  if result:
    session['operator'] = result
    return redirect('/')
  else:
    return render_template('operator_login.html',wrong=True)

# admin home page
@app.route('/admin_page')
def admin_page():
  operator = Operators.query.all()
  symptoms = Symptoms.query.all()
  if session.get("signin_key") == 'sadewiapexfdiblrnnwuludogkqyuazp':
    return render_template('admin_page.html', operator=operator, symptoms=symptoms)
  else:
    return render_template('admin_login.html',wrong=False)

# page to create new operators
@app.route('/create_operator')
def create_operator():
  if session.get("signin_key") == 'sadewiapexfdiblrnnwuludogkqyuazp':
    return render_template("create_operator.html")
  else:
    return render_template('admin_login.html',wrong=False)


# route to delete operators
@app.route('/delete_operator')
def delete_operator():
  if session.get("signin_key") == 'sadewiapexfdiblrnnwuludogkqyuazp':
    op_id = request.args.get('op_id')
    Operators.query.filter_by(op_id=op_id).delete()
    db.session.commit()
    return redirect('/admin_page')
  else:
    return render_template('admin_login.html',wrong=False)

# route to delete symptoms
@app.route('/delete_symptom')
def delete_symptom():
  if session.get("signin_key") == 'sadewiapexfdiblrnnwuludogkqyuazp':
    symptom_id = request.args.get('symptom_id')
    Symptoms.query.filter_by(symptom_id=symptom_id).delete()
    db.session.commit()
    return redirect('/admin_page')
  else:
    return render_template('admin_login.html',wrong=False)


# commit operator details
@app.route('/get_operator_data')
def get_operator_data():
  if session.get("signin_key") == 'sadewiapexfdiblrnnwuludogkqyuazp':
    name = request.args.get('name')
    email = request.args.get('email')
    password = request.args.get('password')
    date_created = datetime.now()
    op_id = random.randint(100000,999999)
    new_op = Operators(name=name, email=email, password=password, date_created=date_created, op_id=op_id)
    db.session.add(new_op)
    db.session.commit()
    return redirect("/admin_page")
  else:
    return render_template('admin_login.html',wrong=False)

# commit operator details
@app.route('/get_symptom')
def get_symptom():
  if session.get("signin_key") == 'sadewiapexfdiblrnnwuludogkqyuazp':
    name = request.args.get('name')
    symptom_id = random.randint(100000,999999)
    date_created = datetime.now()
    new_symptom = Symptoms(name=name, date_created=date_created, symptom_id=symptom_id)
    db.session.add(new_symptom)
    db.session.commit()
    return redirect("/admin_page")
  else:
    return render_template('admin_login.html',wrong=False)

# help page
@app.route('/help')
def help():
  return render_template('help.html')

if __name__ == "__main__":
  app.run(debug=True)