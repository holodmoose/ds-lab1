from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool
import os

if not os.getenv("TESTING"):
    # Database configuration from environment variables
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    DB_NAME = os.getenv("POSTGRES_DB", "postgres")
    DB_HOST = os.getenv("DB_HOST", "postgres")
    DB_PORT = os.getenv("DB_PORT", "5432")

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # SQLAlchemy setup
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
else:
    # For tests, create minimal setup
    Base = declarative_base()

    # Настройка тестовой базы данных (SQLite в памяти)
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


# Database model
class PersonDB(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    address = Column(String, nullable=False)
    work = Column(String, nullable=False)


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models
class PersonBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    age: int
    address: str
    work: str


class PersonCreate(PersonBase):
    pass


class PersonResponse(PersonBase):
    id: int


class ErrorResponse(BaseModel):
    message: str


def error_response(msg, code):
    return JSONResponse(
        content=ErrorResponse(message=msg).model_dump(), status_code=code
    )


# FastAPI app
app = FastAPI(title="Persons API", root_path="/api/v1")


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_person_by_id(id, db):
    person = db.query(PersonDB).filter(PersonDB.id == id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Not found")
    return person


@app.get("/persons/{person_id}", response_model=PersonResponse)
def read_person(person_id: int, db: Session = Depends(get_db)):
    return get_person_by_id(person_id, db)


@app.get("/persons", response_model=list[PersonResponse])
def read_persons(db: Session = Depends(get_db)):
    return db.query(PersonDB).all()


@app.post("/persons", status_code=status.HTTP_201_CREATED)
def create_person(
    person: PersonCreate, response: Response, db: Session = Depends(get_db)
):
    db_person = PersonDB(**person.model_dump())
    db.add(db_person)
    db.commit()
    db.refresh(db_person)

    # Set Location header with the path to the created resource
    response.headers["Location"] = f"/persons/{db_person.id}"
    return None  # Empty body


@app.patch("/persons/{person_id}", response_model=PersonResponse)
def update_person(person_id: int, person: dict, db: Session = Depends(get_db)):
    db_person = get_person_by_id(person_id, db)

    for field, value in person.items():
        if not getattr(db_person, field):
            return error_response("Invalid data", 400)
        setattr(db_person, field, value)

    db.commit()
    db.refresh(db_person)
    return db_person


@app.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = get_person_by_id(person_id, db)

    db.delete(person)
    db.commit()
