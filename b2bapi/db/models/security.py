from . import db

class Word(db.Model):
    __tablename__ = 'reserved_words'

    word_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.Unicode, unique=True, nullable=False)
    dictionary = db.Column(db.Unicode)
