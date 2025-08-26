from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Dict
import json

Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime)

def _deserialize(msg):
        try:
            return json.loads(msg.content)
        except Exception:
            return msg.content

class PostgreSQLSession:
    """
    PostgreSQL-backed session for storing chat messages.
    """

    
    def __init__(self, session_id: str, db_url: str):
        self.session_id = session_id
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    async def append(self, message: Dict[str, str]):
        with self.Session() as db:
            db.add(Message(
                id=f"{self.session_id}_{datetime.utcnow().isoformat()}",
                session_id=self.session_id,
                role=message['role'],
                content=message['content'],
                timestamp=datetime.utcnow()
            ))
            db.commit()

    async def get_items(self) -> List[Dict[str, str]]:
        with self.Session() as db:
            messages = db.query(Message).filter_by(session_id=self.session_id).order_by(Message.timestamp).all()
            return [
                {
                    "role": m.role,
                    "content": _deserialize(m)
                }
                for m in messages
            ]


        
    async def add_items(self, message: Dict[str, str]):
        return await self.append(message)

    async def add_items(self, messages: List[Dict[str, str]]):
        with self.Session() as db:
            for msg in messages:
                db.add(Message(
                    id=f"{self.session_id}_{datetime.utcnow().isoformat()}",
                    session_id=self.session_id,
                    role=msg['role'],
                    content=json.dumps(msg['content']),  # 🛠 serialize content
                    timestamp=datetime.utcnow()
                ))
            db.commit()



    async def clear_session(self) -> None:
        with self.Session() as db:
            db.query(Message).filter_by(session_id=self.session_id).delete()
            db.commit()
