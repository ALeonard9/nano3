from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Boardgame, Base, BGItem, User

engine = create_engine('sqlite:///bgdb.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Leo Battiglia", email="LeoNineStudios@outlook.com",
             picture='https://s3.amazonaws.com/leoninestudios/favicon.ico')
session.add(User1)
session.commit()

# Menu for UrbanBurger
boardgame1 = Boardgame(name="Monopoly", user_id=1)

session.add(boardgame1)
session.commit()

bgItem2 = BGItem(user_id=1, name="$500", description="Currency",
                     quantity=10, boardgame=boardgame1)

session.add(bgItem2)
session.commit()


bgItem1 = BGItem(user_id=1, name="$100", description="Currency",
                     quantity=20, boardgame=boardgame1)

session.add(bgItem1)
session.commit()

bgItem3 = BGItem(user_id=1, name="Dice", description="Dice for rolling",
                     quantity=2, boardgame=boardgame1)

session.add(bgItem3)
session.commit()

bgItem4 =BGItem(user_id=1, name="Player Markers", description="Metal Tokens.",
                     quantity=8, boardgame=boardgame1)
session.add(bgItem4)
session.commit()

boardgame2 = Boardgame(name="Ticket To Ride", user_id=1)

session.add(boardgame2)
session.commit()


bgItem1 = BGItem(user_id=1, name="Trains", description="Plastic Trains",
                     quantity=45, boardgame=boardgame2)

session.add(bgItem1)
session.commit()

bgItem2 = BGItem(user_id=1, name="Resources", description="Plastic Cards",
                     quantity=200, boardgame=boardgame2)
session.add(bgItem2)
session.commit()


boardgame3 = Boardgame(name="Cards Against Humanity", user_id=1)

session.add(boardgame3)
session.commit()


bgItem1 = BGItem(user_id=1, name="Cards", description="Plastic Cards",
                     quantity=300, boardgame=boardgame3)

session.add(bgItem1)
session.commit()

print "added menu items!"
