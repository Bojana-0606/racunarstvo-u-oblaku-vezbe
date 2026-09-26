import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://knjige:knjige_demo@db:5432/knjige"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Knjiga(Base):
    __tablename__ = "knjige"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    naslov: Mapped[str] = mapped_column(String(200), nullable=False)
    autor: Mapped[str] = mapped_column(String(120), nullable=False)
    godina: Mapped[int | None] = mapped_column(Integer, nullable=True)


class KnjigaUnos(BaseModel):
    naslov: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=120)
    godina: int | None = Field(default=None, ge=0, le=2100)


class KnjigaIzlaz(KnjigaUnos):
    model_config = ConfigDict(from_attributes=True)
    id: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Evidencija knjiga", version="1.0.0", lifespan=lifespan)


def sesija():
    with SessionLocal() as db:
        yield db


@app.get("/zdravlje")
def zdravlje():
    return {"status": "ok"}


@app.post("/knjige", response_model=KnjigaIzlaz, status_code=status.HTTP_201_CREATED)
def dodaj_knjigu(podaci: KnjigaUnos, db: Session = Depends(sesija)):
    knjiga = Knjiga(**podaci.model_dump())
    db.add(knjiga)
    db.commit()
    db.refresh(knjiga)
    return knjiga


@app.get("/knjige", response_model=list[KnjigaIzlaz])
def sve_knjige(db: Session = Depends(sesija)):
    return db.scalars(select(Knjiga).order_by(Knjiga.id)).all()


@app.get("/knjige/{knjiga_id}", response_model=KnjigaIzlaz)
def jedna_knjiga(knjiga_id: int, db: Session = Depends(sesija)):
    knjiga = db.get(Knjiga, knjiga_id)
    if knjiga is None:
        raise HTTPException(status_code=404, detail="Knjiga nije pronađena")
    return knjiga


@app.put("/knjige/{knjiga_id}", response_model=KnjigaIzlaz)
def izmeni_knjigu(knjiga_id: int, podaci: KnjigaUnos, db: Session = Depends(sesija)):
    knjiga = db.get(Knjiga, knjiga_id)
    if knjiga is None:
        raise HTTPException(status_code=404, detail="Knjiga nije pronađena")
    for polje, vrednost in podaci.model_dump().items():
        setattr(knjiga, polje, vrednost)
    db.commit()
    db.refresh(knjiga)
    return knjiga


@app.delete("/knjige/{knjiga_id}", status_code=status.HTTP_204_NO_CONTENT)
def obrisi_knjigu(knjiga_id: int, db: Session = Depends(sesija)):
    knjiga = db.get(Knjiga, knjiga_id)
    if knjiga is None:
        raise HTTPException(status_code=404, detail="Knjiga nije pronađena")
    db.delete(knjiga)
    db.commit()
