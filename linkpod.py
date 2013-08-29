#!/usr/bin/env python
#-*- coding:utf-8 -*-
import MySQLdb
import urllib2
import re
import hashlib
from flask import Flask, g, request, session, escape
from flask import render_template, url_for, redirect, Markup

app = Flask(__name__)
app.debug = True

from sae.const import (MYSQL_HOST, MYSQL_HOST_S,
    MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DB
)
@app.before_request
def before_request():
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    g.db = MySQLdb.connect(MYSQL_HOST, MYSQL_USER, MYSQL_PASS,
                           MYSQL_DB, port=int(MYSQL_PORT),
                           charset="utf8")
@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'): g.db.close()

@app.route('/')
def index():
    email = session.get('email')
    return render_template('index.html',email=email)


@app.route('/signup',methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        password = hashlib.md5(request.form['password']).hexdigest()
        adduser_result = adduser(request.form['email'],password)
        return redirect(url_for('signin'))
    return render_template('signup.html')



@app.route('/signin',methods=['GET', 'POST'])
def signin():
    signin_failed = False
    if request.method == 'POST':
        password = hashlib.md5(request.form['password']).hexdigest()
        userid = verifiuser(request.form['email'],password)
        if userid:
            session['user_id'] = userid
            session['email'] = request.form['email']
            return redirect(url_for('site'))
        else:
            signin_failed = True
    return render_template('signin.html',signin_failed=signin_failed)


@app.route('/logout')
def logout():
    # 如果会话中有用户名就删除它
    session.pop('user_id', None)
    session.pop('email', None)
    return redirect(url_for('index'))

@app.route('/site',methods=['GET', 'POST'])
@app.route('/site/<domain>',methods=['GET', 'POST'])
def site(domain=None,userid=None):
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    userid = session['user_id']
    email = session['email']
    if domain:
        siteinfo = getsiteinfo(domain)
        if request.method == 'POST':
            if request.form['action'] == 'add':
                addlink_result = addlink(domain,request.form['domain'],request.form['linkname'],request.form['linktype'])
            elif  request.form['action'] == 'delete':
                deletelink_result = deletelink(request.form['linkid'])
            elif  request.form['action'] == 'modifysite':
                modifysite_result = modifysite(siteinfo[0],request.form['sitename'],request.form['alivvid'])
        links = getlinks(domain)
        #siteid,sitetype,sitedomain,sitename,alivvid = siteinfo
        return render_template('links.html',links=links,domain=domain,siteinfo=siteinfo)
    else:
        if request.method == 'POST':
            if request.form['action'] == 'add':
                addsite_result = addsite(request.form['domain'],request.form['sitename'],userid)
            elif  request.form['action'] == 'delete':
                deletesite_result = deletesite(request.form['siteid'])

        sites = getsites(userid)
        return render_template('sites.html',sites=sites,email=email)

@app.route('/link')
@app.route('/link/<domain>')
def link(domain=None):
    if domain:
        links = getlinks(domain)
        siteinfo = getsiteinfo(domain)
        alivvid = siteinfo[-1]
        alivvlink = ""
        if alivvid:
            alivvlink = urllib2.urlopen("http://vvtui.net/htmlcode.aspx?type=3&code=1&wid=%s"%alivvid).read()
            alivvlink = urllib2.unquote(alivvlink).decode("utf-8")
            alivvlink = alivvlink.replace("</a>","</a> ")
        return render_template('linkpage.html',links=links,alivvlink=Markup(alivvlink),encode="gb2312")
    else:
        return 'This is a Link Page!'

@app.route('/getcode/<domain>')
def getcode(domain=None,domaincode='xxxxxxx'):
    if domain:
        code = getcode(domain)
        return render_template('getcode.html',domain=domain,domaincode=domaincode)
    else:
        return 'This is a Link Page!'

@app.route('/getlink/<domain>')
def getlink(domain=None,domaincode='xxxxxxx'):
    if domain:
        html = urllib2.urlopen('http://'+domain).read()
        p = re.compile( r'<a.+?href=.+?>.+?</a>' )
        pname = re.compile( r'(?<=>).*?(?=</a>)' )
        phref = re.compile( r'(?<=href\=\").*?(?=\")' )
        linklist = p.findall(html)
        keys = [domain,'javascript','onclick','<img']
        newlist = []
        result = ''

        for link in linklist:
        
            x = True
            for key in keys:
                if key in link.decode('utf-8'):
                    x = False
            if x and 'href="http://' in link.decode('utf-8'):
                newlist.append(link)
        for nlink in newlist:    
            linkname = pname.findall(nlink)
            if linkname:linkname = linkname[0]
            else:continue
            linkhref = phref.findall(nlink)
            if linkhref:linkhref = linkhref[0]
            else:continue
            checkresult = checklink(domain,linkhref,linkname)
            if checkresult:
                if not addlink(domain,linkhref,linkname):
                    return 'no'+linkname+'>'+linkhref+'<br>'
            result +=str(checkresult)+'>'+linkname+'>'+linkhref+'<br>'
        return result
    else:
        return 'This is a GetLink Page!'

def adduser(email,password):
    sql = g.db.cursor()
    result = sql.execute("insert into linkpod_user(email,password) values('%s','%s')"%(email,password))
    if result:
        return True

def verifiuser(email,password):
    sql = g.db.cursor()
    sql.execute("select id,password from linkpod_user where email='%s'"%email)
    result = sql.fetchone()
    if password == result[1]:
        return int(result[0])


def addsite(domain,sitename,userid,keyname=None):
    sql = g.db.cursor()
    result = sql.execute("insert into linkpod_site(user_id,site_domain,site_name) values(%s,'%s','%s')"%(userid,domain,sitename))
    if result:
        return True

def getsites(userid):
    sql = g.db.cursor()
    sql.execute("select * from linkpod_site where user_id=%s"%userid)
    result = list(sql.fetchall())
    result.reverse()
    if result:
        return result

def getsiteid(domain):
    sql = g.db.cursor()
    sql.execute("select id from linkpod_site where site_domain='%s'"%domain)
    result = sql.fetchall()
    if result:
        return int(result[0][0])

def getsiteinfo(domain):
    sql = g.db.cursor()
    sql.execute("select * from linkpod_site where site_domain='%s'"%domain)
    result = sql.fetchone()
    if result:
        return result

def deletesite(siteid):
    sql = g.db.cursor()
    result = sql.execute("delete from linkpod_site where id=%s"%int(siteid))
    if result:
        return True

def addlink(domain,linkdomain,linkname,linktype=1):
    sql = g.db.cursor()
    siteid = getsiteid(domain)
    if not siteid:
        return False
    result = sql.execute("insert into linkpod_link(site_id,link_domain,link_name) values(%s,'%s','%s')"%(siteid,linkdomain,linkname))
    if result:
        return True

def checklink(domain,linkdomain,linkname):
    siteid = getsiteid(domain)
    if not siteid:
        return False
    sql = g.db.cursor()
    sql.execute("select count(*) from linkpod_link where site_id=%s and link_domain='%s' and link_name='%s' "%(siteid,linkdomain,linkname))
    result = sql.fetchall()
    return result
    '''
    if result[0]:
        return False
    else:
        return True
    '''
def getlinks(domain):
    siteid = getsiteid(domain)
    if not siteid:
        return False
    sql = g.db.cursor()
    sql.execute("select * from linkpod_link where site_id=%s"%siteid)
    result = list(sql.fetchall())
    result.reverse()
    if result:
        return result

def deletelink(linkid):
    sql = g.db.cursor()
    result = sql.execute("delete from linkpod_link where id=%s"%int(linkid))
    if result:
        return True

def modifysite(siteid,sitename,alivvid=""):
    sql = g.db.cursor()
    result = sql.execute("update linkpod_site set site_name='%s',alivvid='%s' where id=%s"%(sitename,alivvid,int(siteid)))
    if result:
        return True
