from . import db

class CommonWord(db.Model):
    """
    This model can be useful to prevent some easily guessable passwords.
    """
    __tablename__ = 'common_words'

    word_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.Unicode, unique=True, nullable=False)


class ReservedWord(db.Model):
    """
    This model can be used to prevent subdomain registration with potentially
    problematic words.
    """
    __tablename__ = 'reserved_words'

    word_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.Unicode, unique=True, nullable=False)
