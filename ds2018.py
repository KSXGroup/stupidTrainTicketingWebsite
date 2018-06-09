from flask import Flask
from flask import request, render_template, abort, redirect, url_for, session
from datetime import datetime, timedelta
from subprocess import Popen, PIPE, STDOUT
import fcntl, os, json, re
import pdb

app = Flask(__name__)

# set it to a random string
app.secret_key = 'fuckyouaaaaaaaa'

# set this to path/to/your/database/backend/program
database_exec_path = './code'

def app_init():
    app.proc = Popen([database_exec_path], stdin=PIPE, stdout=PIPE)
    fd = app.proc.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

app_init()

def db_write(cmd):
    cmdlist = re.split(r'[ ]', cmd)
    for cmdb in cmdlist:
        app.proc.stdin.write((cmdb + '\n').encode())
        app.proc.stdin.flush()

def db_readline():
    res = ""
    line = ""
    while True:
        try:
            line = app.proc.stdout.read().decode('utf-8')
            if line == "" or line == "\n":
                return res
            else:
                res += line
        except:
            break
    return res

def db_communicate(cmd):
    line = ""
    res = ""
    if cmd == "":
        return ""
    else:
        db_write(cmd)
        while line == "":
            line = db_readline()
        res += line
        while True:
            line = db_readline()
            if line != "":
                res += line
            else:
                break
        print(cmd)
        print(res)
        return res

def getDateStrings():
    ret =  []
    a = datetime.utcnow()
    a += timedelta(hours=8)
    a1 = a + timedelta(days=30)
    s = str(a.year) + "年" + str(a.month) + "月" + str(a.day) + "日"
    s1 = str(a1.year) + "年" + str(a1.month) + "月" + str(a1.day) + "日"
    ret.append(s)
    ret.append(s1)
    return ret

def getAllorder(userid, catalog):
    currentDate = datetime.utcnow() + timedelta(hours=8)
    ret = []
    for i in range(1,31):
        syear = str(currentDate.year)
        smonth = str(currentDate.month)
        sday = str(currentDate.day)
        if len(smonth) == 1: smonth = '0' + smonth
        if len(sday) == 1: sday = '0' + sday
        datetmp = syear + '-' + smonth + '-' + sday
        cmdtmp = ' '.join(['query_order',str(userid), datetmp, str(catalog)])
        res = db_communicate(cmdtmp)
        tmptable = re.split(r'\n', res)
        if tmptable[len(tmptable) - 1] == "": tmptable.pop()
        if tmptable[0] == "0":
            currentDate += timedelta(days = 1)
            continue
        print(tmptable)
        if len(ret) > 0 :
            ret[0]  = int(ret[0]) + int(tmptable[0])
            for j in range(1, len(tmptable)):
                ret.append(tmptable[j])
        else:
            ret  = tmptable
        currentDate += timedelta(days = 1)
    print(ret)
    for i in range(1, len(ret)):
        ret[i] = re.split(r' ', ret[i])
    return ret


@app.route('/index', methods=['GET'])
@app.route('/', methods=['GET'])
def home():
    if request.method == 'GET':
        if 'home_success_info' in session and session['home_success_info'] != '':
            success_info = session['home_success_info']
            session.pop('home_success_info', None)
        else:
            success_info = None
        if 'home_err_info' in session and session['home_err_info'] != '':
            err_info = session['home_err_info']
            session.pop('home_err_info', None)
        else:
            err_info = None
        if 'user_id' in session and 'user_name' in session and session['user_name'] != '':
            user_name = session['user_name']
        else:
            user_name = None
        return render_template('index.html', success_info=success_info, err_info=err_info, user_name=user_name)

@app.route('/queryRes', methods=['GET', 'POST'])
def queryRes():
    resList = []
    retList = []
    if request.method == 'POST':
        loc1 = request.form['loc1']
        loc2 = request.form['loc2']
        ddate = request.form['ddate']
        if request.form['id'] == 'queryRes':
            if loc1 == "" or loc2 == "" or ddate == "":
                return json.dumps("")
            qcmd = ' '.join(['query_ticket', loc1, loc2, ddate])
            qcmd += " CDGKOTZ"
            qstring = db_communicate(qcmd)
            resList = re.split(r'\n', qstring)
            for item in resList:
                retList.append(re.split(r'[ ]', item))
            restmp = retList[1 : len(retList) - 1]
            restmp = sorted(restmp, key = lambda item : item[3].lower())
            for i in range(1, len(resList) - 1):
                retList[i] = restmp[i - 1]
            retList.pop()
            qRes = json.dumps(retList)
            return qRes
        else:
            return render_template('queryRes.html', loc1 = loc1, loc2 = loc2, ddate = ddate, postFrom = request.form['id'])
    else:
        if 'user_id' in session and 'user_name' in session and session['user_name'] != '':
            user_name = session['user_name']
        else:
            user_name = None
        return render_template('queryRes.html', user_name = user_name)

@app.route('/signin', methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        reply = db_communicate(' '.join(['login', userid, password]))
        print(reply)
        if reply == '0' or reply == 'Wrong Command':
            return render_template('signin.html', err_info='Login failed for some reason.')
        else:
            session['home_success_info'] = 'Logged in successfully! Now you can play around.'
            session['user_id'] = userid
            reply = db_communicate(' '.join(['query_profile', userid]))
            if reply == '0':
                session['home_err_info'] = 'Login failed! User does not exist.'
            else:
                session['user_name'] = reply.split(' ')[0]
            return redirect(url_for('home'))
    else:
        return render_template('signin.html')

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        repassword = request.form['repassword']
        if password != repassword:
            return render_template('signup.html', err_info='The two passwords you typed do not match.')
        reply = db_communicate(' '.join(['register', name, password, email, phone]))
        if reply == '-1':
            return render_template('signup.html', err_info='Registration failed for some reason.')
        else:
            userid = int(reply)
            session['home_success_info'] = 'Registration successful! Your account ID is %s.' % (userid)
            return redirect(url_for('home'))
    else:
        if 'user_id' in session and 'user_name' in session and session['user_name'] != '':
            user_name = session['user_name']
        else:
            user_name = None
        return render_template('signup.html', user_name = user_name)

@app.route('/signout', methods=['GET'])
def signout():
    if 'user_id' in session:
        session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        session['home_err_info'] = 'Error! You have not signed in.'
        return redirect(url_for('home'))
    user_id = session['user_id']
    reply = db_communicate(' '.join(['query_profile', user_id]))
    if reply == '0':
        session['home_err_info'] = 'Error! User does not exist.'
        return redirect(url_for('home'))
    else:
        vec = reply.split(' ')
        user_name = vec[0]
        user_email = vec[1]
        user_phone = vec[2]
        user_priv = vec[3]
    return render_template('profile.html', user_id=user_id, user_name=user_name, user_email=user_email, user_phone=user_phone, user_priv=user_priv)

@app.route('/settings', methods=['POST', 'GET'])
def settings():
    if 'user_id' not in session:
        session['home_err_info'] = 'Error! You have not signed in.'
        return redirect(url_for('home'))
    if request.method == 'POST':
        user_id = session['user_id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        repassword = request.form['repassword']
        if password != repassword:
            return render_template('settings.html', err_info='The two passwords you typed do not match.')
        reply = db_communicate(' '.join(['modify_profile', user_id, name, password, email, phone]))
        if reply == '0':
            return render_template('settings.html', err_info='Modification failed for some reason.')
        else:
            session['home_success_info'] = 'Profile modified successfully!'
            return redirect(url_for('home'))
    else:
        user_name = session['user_name']
        return render_template('settings.html', user_name=user_name)

@app.route('/orderTic', methods=['POST', 'GET'])
def orderTic():
    if request.method == 'POST':
        if 'user_id' in session and 'user_name' in session and session['user_name'] != '':
            user_name = session['user_name']
            user_id = session['user_id']
        else:
            user_name = None
            user_id = None
        if user_id != "":
            if request.form['form-name'] == "sorder":
                order_trainid = request.form['order-train-id']
                order_loc1 = request.form['order-loc1']
                order_loc2 = request.form['order-loc2']
                order_date = request.form['order-date']
                order_kind = request.form['order-kind']
                order_time1 = request.form['order-time1']
                order_time2 = request.form['order-time2']
                order_price = request.form['order-price']
                order_left = request.form['order-left']
                return render_template('orderTic.html',user_name = session['user_name'], train_id = order_trainid, tic_loc1 = order_loc1, tic_loc2 = order_loc2, tic_date = order_date, tic_type = order_kind, tic_price = order_price, tic_left = order_left, tic_time1 = order_time1, tic_time2 = order_time2)
            else:
                if request.form['form-name'] == "corder":
                    corder_trainid = request.form['corder-train-id']
                    corder_type = request.form['corder-type']
                    corder_loc1 = request.form['corder-loc1']
                    corder_loc2 = request.form['corder-loc2']
                    corder_date = request.form['corder-date']
                    corder_num = request.form['corder-num']
                    btcmd = ' '.join(['buy_ticket', session['user_id'], corder_num, corder_trainid, corder_loc1, corder_loc2, corder_date, corder_type])
                    return json.dumps(db_communicate(btcmd))
                else:
                    return json.dumps("0")
        else:
            err_info = "未登录"
            return render_template('orderTic.html', err_info = err_info)
    else:
        err_info = "禁止访问"
        return render_template('orderTic.html', err_info = err_info)



@app.route('/userZone', methods=['GET', 'POST'])
def userZone():
    if request.method == 'GET':
        timeTuple = getDateStrings()
        if 'user_id' in session and 'user_name' in session and session['user_name'] != '':
            user_name = session['user_name']
            user_id = session['user_id']
        else:
            user_name = None
            user_id = None
        retStatus = request.args.get('status')
        if retStatus == "" or retStatus == " " or retStatus == None: return render_template('userZone.html',  user_name = user_name, user_id = str(user_id) , current_time = timeTuple[0], final_time = timeTuple[1], status = "welcome")
        else: return render_template('userZone.html',  user_name = user_name, user_id = str(user_id) , current_time = timeTuple[0], final_time = timeTuple[1], status = retStatus)
    if request.method == 'POST':
        if 'user_id' in session and 'user_name' in session and session['user_name'] != '':
            user_name = session['user_name']
            user_id = session['user_id']
            return json.dumps(getAllorder(user_id, 'CDGKTZO'))
        else:
            return json.dumps("0")

@app.route('/debugger', methods=['GET', 'POST'])
def debugger():
    if request.method == 'POST':
        order = request.form['order']
        if len(order.strip('\n')) == 0:
            return render_template("debugger.html")
        res = ""
        if order != "":
            res = db_communicate(order)
        return render_template("debugger.html")
    else:
        return render_template("debugger.html")

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 80, debug=True)

