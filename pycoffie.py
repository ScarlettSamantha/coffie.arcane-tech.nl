import os
import datetime
import random
import zlib
import math

from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(os.path.dirname(__file__)) + '/db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Actor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    in_session = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return '%s' % self.name


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id'), nullable=False)
    actor = db.relationship('Actor', backref=db.backref('events', lazy=True))


def get_people():
    return Actor.query.all()

@app.cli.command()
def init_db():
    db.create_all()

@app.cli.command()
def deinit_db():
    db.drop_all()

@app.cli.command()
def reinit_db():
    deinit_db()
    init_db()


@app.route('/', methods=['get'])
def index():
    return render_template('index.html', people=get_people())


@app.route('/add/', methods=['post'])
def add_person_to_session():
    if request.form.get('id') is None:
        na = Actor(name=request.form.get('name'))
        db.session.add(na)
        db.session.commit()
        return redirect(url_for('index', _scheme='https', _external=True))
    else:
        na = Actor.query.filter_by(id=request.form.get('id')).first()
        na.in_session = True
        db.session.commit()
        return '200'



@app.route('/remove/', methods=['post'])
def remove_person_from_session():
    na = Actor.query.filter_by(id=request.form.get('id')).first()
    if na is not None:
        na.in_session = False
        db.session.commit()
    return '200'


@app.route('/choose/', methods=['get'])
def choose_from_session():
    suitable_actors = Actor.query.filter_by(in_session=True).all()
    actor_key_index = {}
    roll_results = {}
    times_to_reroll = 20000
    for index, a in enumerate(suitable_actors):
        actor_key_index[index] = a
        roll_results[index] = 0
    seed = zlib.crc32(str(datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')).encode()) + zlib.crc32(request.headers.get('User-Agent').encode())
    random.seed(seed)
    roll_results_keys_cache = list(roll_results.keys())
    for _ in range(times_to_reroll):
        roll_results[random.choice(roll_results_keys_cache)] += 1
    reverse_sorted_actors_by_win = sorted(roll_results, key=lambda x: roll_results[x])
    ca = actor_key_index[reverse_sorted_actors_by_win[-1]]
    e = Event(actor=ca)
    db.session.add(e)
    db.session.commit()
    result_string = []
    for zp in reversed(reverse_sorted_actors_by_win):
        result_string.append('%s @ %s%% %s/%s' % (actor_key_index[zp].name, round((roll_results[zp]/times_to_reroll)*100, 2), roll_results[zp], times_to_reroll))
    return '%s at %s%% of %s iteraties \n\nbreakdown: \n\n%s' % (ca.name, round((roll_results[reverse_sorted_actors_by_win[-1]]/times_to_reroll)*100, 2), times_to_reroll, '\n'.join(result_string))


if __name__ == '__main__':
    app.run(port=5000)
