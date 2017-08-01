from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import *
from sqlalchemy import inspect

_engine = create_engine(dburl)
Session = sessionmaker(bind=_engine)
Base = declarative_base()
class User(Base):
    __tablename__ = 'users'
    sha = Column(String(64), primary_key = True)
    access = Column(Integer, default=0)

    def __init__(self, **kwargs):
        self.sha = kwargs.pop('sha', None)
        self.access = kwargs.pop('access', 0)

class Guild(Base):
    __tablename__ = 'guilds'
    sha = Column(String(64), primary_key = True)
    prefix = Column(String(), default='!')

    def __init__(self, **kwargs):
        self.sha = kwargs.get('sha', None)
        self.prefix = kwargs.get('prefix', '!')

def validate_dbo(dbo):
    if(len(getattr(dbo, 'sha', '')) != 64):
        raise ValueError('Invalid DBO/SHA: '+repr(dbo))

def merge(dbo):
    """Merge object into the db. Must have valid sha."""
    validate_dbo(dbo)
    session = Session()
    session.merge(dbo)
    session.commit()
    session.close()

def pull(dbo):
    """Populate object with data from the db. Must have valid sha. If sha doesn't exist in the db, no fields get pulled."""
    validate_dbo(dbo)
    session = Session()
    query = session.query(type(dbo)).filter(type(dbo).sha == dbo.sha)
    i = query.one_or_none()
    if(i):
        for attr in i.__dict__:
            setattr(dbo, attr, getattr(i, attr))
    session.close()

Base.metadata.create_all(_engine)
