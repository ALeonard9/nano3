# Import necessary libraries and functions.
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

# Create class for the user table.
class User(Base):
    __tablename__ = 'user'

# Define columns for the user table.
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    picture = Column(String(250))
    email = Column(String(250))

# Serialize for the user table for JSON API.
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'picture'      : self.picture,
           'email'        : self.email
       }

# Create class for the boardgame table.
class Boardgame(Base):
    __tablename__ = 'boardgame'

# Define columns for the boardgame table.
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

# Serialize for the boardgame table for JSON API.
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id
       }

# Create class for the boardgame item table.
class BGItem(Base):
    __tablename__ = 'bg_item'

# Define columns for the boardgame item table.
    name =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    quantity = Column(Integer)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)
    boardgame_id = Column(Integer,ForeignKey('boardgame.id'))
    boardgame = relationship(Boardgame)

# Serialize for the boardgame item table for JSON API.
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'description'  : self.description,
           'id'           : self.id,
           'quantity'      : self.quantity,
           'user_id'      : self.user_id
       }



engine = create_engine('sqlite:///bgdb.db')


Base.metadata.create_all(engine)
